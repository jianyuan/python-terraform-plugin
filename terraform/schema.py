import abc
import dataclasses
import enum
import json
import operator
import typing

import marshmallow

from terraform import fields, settings
from terraform.protos import tfplugin5_1_pb2


class NestingMode(enum.IntEnum):
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


class BaseField(marshmallow.fields.Field):
    terraform_type: typing.Optional[str] = None

    def __init__(
        self,
        *,
        description: typing.Optional[str] = None,
        required: bool = False,
        optional: bool = False,
        computed: bool = False,
        force_new: bool = False,
        sensitive: bool = False,
        **kwargs,
    ):
        # TODO: validate metadata
        metadata = {
            "description": description,
            "required": required,
            "optional": optional,
            "computed": computed,
            "force_new": force_new,
            "sensitive": sensitive,
        }
        super().__init__(**kwargs, **metadata)

    def get_terraform_type(self) -> typing.Any:
        if self.terraform_type is not None:
            return self.terraform_type
        raise NotImplementedError


class BaseNestedField(BaseField):
    terraform_nesting = ...


class Bool(marshmallow.fields.Boolean, BaseField):
    terraform_type = "bool"


class Int(marshmallow.fields.Integer, BaseField):
    terraform_type = "number"


class Float(marshmallow.fields.Float, BaseField):
    terraform_type = "number"


class String(marshmallow.fields.String, BaseField):
    terraform_type = "string"


class List(marshmallow.fields.List, BaseField):
    def __init__(
        self,
        cls_or_instance: typing.Union[BaseField, type],
        *,
        min_items: int = 0,
        max_items: int = 0,
        **kwargs,
    ):
        # TODO: validate metadata
        metadata = {
            "min_items": min_items,
            "max_items": max_items,
        }
        super().__init__(cls_or_instance=cls_or_instance, **kwargs, **metadata)

    def get_terraform_type(self) -> typing.Any:
        return ["list", self.inner.get_terraform_type()]


class Map(marshmallow.fields.Mapping, BaseField):
    def __init__(self, values=None, **kwargs):
        if values is None:
            values = String()
        super().__init__(String(), values, **kwargs)

    def get_terraform_type(self) -> typing.Any:
        if isinstance(self.value_field, Nested) and isinstance(
            self.value_field.nested, Resource
        ):
            value_field = String()
        else:
            value_field = self.value_field

        return ["map", value_field.get_terraform_type()]


class Set(marshmallow.fields.List, BaseField):
    def get_terraform_type(self) -> typing.Any:
        return ["set", self.inner.get_terraform_type()]


class Nested(marshmallow.fields.Nested, BaseField):
    ...


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
    # TODO: subclass BaseField

    schema_version: typing.Optional[int] = None

    def get_terraform_type(self) -> typing.Any:
        return [
            "object",
            {
                field.name: field.get_terraform_type()
                for field in self.declared_fields.values()
            },
        ]

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
                not isinstance(field, fields.Map)
                and hasattr(field, "inner")
                and isinstance(field.inner, fields.Nested)
                and isinstance(field.inner.nested, Resource)
                and not (field.metadata["computed"] and not field.metadata["optional"])
            ):
                print(field.name, field)
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
                attributes[field.name] = Attribute(
                    type=field.get_terraform_type(),
                    description=field.metadata["description"],
                    required=field.required,
                    optional=field.metadata["optional"],
                    computed=field.metadata["computed"],
                    sensitive=field.metadata["sensitive"],
                )
                continue

        return Block(attributes=attributes, block_types=block_types)


@dataclasses.dataclass
class ResourceData(typing.MutableMapping):
    def __init__(self):
        self.data = {}

    def __getitem__(self, key: str) -> typing.Any:
        return self.data[key]

    def __setitem__(self, key: str, value: typing.Any) -> None:
        self.data[key] = value

    def __delitem__(self, key: str) -> None:
        del self.data[key]

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self):
        return iter(self.data)

    def set_id(self, value: str) -> None:
        self[settings.ID_KEY] = value


class Resource(Schema):
    name: str

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
