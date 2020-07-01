import abc
import dataclasses
import enum
import json
import operator
import typing

import marshmallow

from terraform import diffs, fields, settings
from terraform.protos import tfplugin5_1_pb2


class NestingMode(enum.Enum):
    INVALID = enum.auto()
    SINGLE = enum.auto()
    GROUP = enum.auto()
    LIST = enum.auto()
    SET = enum.auto()
    MAP = enum.auto()

    def to_proto(self) -> tfplugin5_1_pb2.Schema.NestedBlock.NestingMode:
        return NESTING_MODE_PROTO_ENUMS[self]


NESTING_MODE_PROTO_ENUMS = {
    NestingMode.INVALID: tfplugin5_1_pb2.Schema.NestedBlock.NestingMode.INVALID,
    NestingMode.SINGLE: tfplugin5_1_pb2.Schema.NestedBlock.NestingMode.SINGLE,
    NestingMode.GROUP: tfplugin5_1_pb2.Schema.NestedBlock.NestingMode.GROUP,
    NestingMode.LIST: tfplugin5_1_pb2.Schema.NestedBlock.NestingMode.LIST,
    NestingMode.SET: tfplugin5_1_pb2.Schema.NestedBlock.NestingMode.SET,
    NestingMode.MAP: tfplugin5_1_pb2.Schema.NestedBlock.NestingMode.MAP,
}


@dataclasses.dataclass
class Attribute:
    type: typing.Any
    description: typing.Optional[str] = None
    required: bool = False
    optional: bool = False
    computed: bool = False
    sensitive: bool = False

    def to_proto(self, *, name: str) -> tfplugin5_1_pb2.Schema.Attribute:
        return tfplugin5_1_pb2.Schema.Attribute(
            name=name,
            type=encode_type(self.type),
            description=self.description,
            required=self.required,
            optional=self.optional,
            computed=self.computed,
            sensitive=self.sensitive,
        )


@dataclasses.dataclass
class Block:
    attributes: typing.Dict[str, Attribute] = dataclasses.field(default_factory=dict)
    block_types: typing.Dict[str, "NestedBlock"] = dataclasses.field(
        default_factory=dict
    )

    def to_proto(self) -> tfplugin5_1_pb2.Schema.Block:
        block = tfplugin5_1_pb2.Schema.Block()

        for name, attribute in sorted(
            self.attributes.items(), key=operator.itemgetter(0)
        ):
            block.attributes.append(attribute.to_proto(name=name))

        for name, block_type in sorted(
            self.block_types.items(), key=operator.itemgetter(0)
        ):
            block.block_types.append(block_type.to_proto(name=name))

        return block


@dataclasses.dataclass
class NestedBlock:
    nesting: NestingMode
    block: Block = dataclasses.field(default_factory=Block)
    min_items: int = 0
    max_items: int = 0

    def to_proto(self, *, name: str) -> tfplugin5_1_pb2.Schema.NestedBlock:
        return tfplugin5_1_pb2.Schema.NestedBlock(
            type_name=name,
            block=self.block.to_proto(),
            nesting=self.nesting.to_proto(),
            min_items=self.min_items,
            max_items=self.max_items,
        )


def encode_type(obj: typing.Any) -> bytes:
    return json.dumps(obj, separators=(",", ":")).encode("ascii")


class SchemaMeta(marshmallow.schema.SchemaMeta, abc.ABCMeta):
    ...


class Schema(marshmallow.Schema, metaclass=SchemaMeta):
    schema_version: typing.Optional[int] = None

    def get_terraform_type(self) -> typing.Any:
        return [
            "object",
            {
                field.name: field.get_terraform_type()
                for field in self.declared_fields.values()
            },
        ]

    @marshmallow.pre_dump
    def none_missing(self, data, **kwargs):
        return {key: value for key, value in data.items() if value is not None}

    def get_by_path(
        self, path: typing.Optional[typing.Sequence[str]]
    ) -> typing.List[typing.Union["Schema", fields.BaseField]]:
        current = self

        if not path:
            return [current]

        result = []

        path = path.copy()[::-1]

        while path:
            part = path.pop()

            if isinstance(current, fields.BaseField) and current.primitive:
                if path:
                    return None

            elif isinstance(current, Schema):
                try:
                    current = current.declared_fields[part]
                except KeyError:
                    return None

            elif isinstance(current, fields.List):
                is_index = len(path) > 0 and path[0] == "#"

                current = current.get_inner()
                if isinstance(current, fields.Nested):
                    current = current.schema

                if is_index:
                    part = path.pop()
                    try:
                        int(part)
                    except ValueError:
                        return None

            elif isinstance(current, fields.Map):
                current = current.get_inner()

            else:
                raise NotImplementedError

            result.append(current)

        return result

    def to_proto(self) -> tfplugin5_1_pb2.Schema:
        return tfplugin5_1_pb2.Schema(
            version=self.schema_version, block=self.to_block().to_proto(),
        )

    def to_block(self) -> Block:
        attributes = {}
        block_types = {}

        for field in self.declared_fields.values():
            field = typing.cast(fields.BaseField, field)

            if (
                (
                    (
                        isinstance(field, fields.Map)
                        and not isinstance(
                            field.value_field, (Resource, fields.BaseField)
                        )
                    )
                    or (
                        isinstance(field, fields.List)
                        and isinstance(field.inner, fields.Nested)
                        and isinstance(field.inner.nested, Schema)
                    )
                )
                # Computed-only fields are always handled as attributes
                and not (field.metadata["computed"] and not field.metadata["optional"])
            ):
                if isinstance(field, fields.Set):
                    nesting = NestingMode.SET
                elif isinstance(field, fields.List):
                    nesting = NestingMode.LIST
                elif isinstance(field, fields.Map):
                    nesting = NestingMode.MAP
                else:
                    raise NotImplementedError

                min_items = field.metadata["min_items"]
                max_items = field.metadata["max_items"]

                if field.required and field.metadata["min_items"] == 0:
                    min_items = 1

                if field.metadata["optional"] and field.metadata["min_items"] > 0:
                    min_items = 0

                if field.metadata["computed"] and not field.metadata["optional"]:
                    min_items = 0
                    max_items = 0

                block_types[field.name] = NestedBlock(
                    nesting=nesting,
                    block=field.inner.nested.to_block(),
                    min_items=min_items,
                    max_items=max_items,
                )

            else:
                required = field.required
                optional = field.metadata["optional"]

                # NOTE: See Schema.coreConfigSchemaAttribute for explanation
                if field.required and callable(field.default):
                    try:
                        value = field.default()
                    except Exception:
                        required = False
                        optional = True
                    else:
                        if value is not None:
                            required = False
                            optional = True

                attributes[field.name] = Attribute(
                    type=field.get_terraform_type(),
                    description=field.metadata["description"],
                    required=required,
                    optional=optional,
                    computed=field.metadata["computed"],
                    sensitive=field.metadata["sensitive"],
                )

        return Block(attributes=attributes, block_types=block_types)


@dataclasses.dataclass
class ResourceData(typing.MutableMapping):
    schema: Schema
    config: typing.Dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    state: typing.Optional[diffs.InstanceState] = None
    diff: typing.Optional[diffs.InstanceDiff] = None
    meta: typing.Dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    timeouts = ...
    provider_meta = ...

    def __getitem__(self, key: str) -> typing.Any:
        return self.config[key]

    def __setitem__(self, key: str, value: typing.Any) -> None:
        self.config[key] = value

    def __delitem__(self, key: str) -> None:
        del self.config[key]

    def __len__(self) -> int:
        return len(self.config)

    def __iter__(self):
        return iter(self.config)

    def get(self, key: str) -> typing.Any:
        ...

    def set_id(self, value: str) -> None:
        self[settings.ID_KEY] = value


class Resource(Schema):
    name: str
    provider: "Provider"

    id = fields.String(optional=True, computed=True)

    def upgrade_state(
        self, *, state: typing.Dict[str, typing.Any], version: int
    ) -> typing.Dict[str, typing.Any]:
        return self.dump(state)

    async def create(self, data: ResourceData):
        ...

    async def read(self, data: ResourceData):
        ...

    async def update(self, data: ResourceData):
        ...

    async def delete(self, data: ResourceData):
        ...

    async def exists(self, data: ResourceData):
        ...


class Resources(typing.Mapping[str, Resource]):
    def __init__(
        self,
        resources: typing.Optional[typing.Sequence[Resource]] = None,
        *,
        provider: "Provider"
    ):
        self.resources: typing.Dict[str, Resource] = {}
        self.provider = provider

        if resources is not None:
            for resource in resources:
                self.add(resource)

    def __getitem__(self, name: str) -> Resource:
        return self.resources[name]

    def __iter__(self):
        return iter(self.resources)

    def __len__(self) -> int:
        return len(self.resources)

    def add(self, resource: Resource):
        resource.provider = self.provider
        self.resources[resource.name] = resource


class Provider(Schema):
    name: str
    terraform_version: typing.Optional[str] = None

    def __init__(
        self,
        resources: typing.Optional[typing.Sequence[Resource]] = None,
        data_sources: typing.Optional[typing.Sequence[Resource]] = None,
    ):
        super().__init__()

        self.resources = Resources(resources, provider=self)
        self.data_sources = Resources(data_sources, provider=self)
        self.config: typing.Dict[str, typing.Any] = {}

    def add_resource(self, resource: Resource):
        self.resources.add(resource)

    def add_data_source(self, data_source: Resource):
        self.data_sources.add(data_source)

    def configure(self, config: typing.Dict[str, typing.Any]):
        self.config = config
