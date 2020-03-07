import dataclasses
import enum
import json
import typing

import marshmallow

from terraform import fields


class NestingMode(enum.IntEnum):
    SINGLE = enum.auto()
    GROUP = enum.auto()
    LIST = enum.auto()
    SET = enum.auto()
    MAP = enum.auto()


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
        from terraform import schema

        if isinstance(self.value_field, Nested) and isinstance(
            self.value_field.nested, schema.Resource
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
    type: bytes
    description: typing.Optional[str] = None
    required: bool = False
    optional: bool = False
    computed: bool = False
    sensitive: bool = False


@dataclasses.dataclass
class Block:
    attributes: typing.Dict[str, Attribute] = dataclasses.field(default_factory=dict)
    block_types: typing.Dict[str, "NestedBlock"] = dataclasses.field(
        default_factory=dict
    )


@dataclasses.dataclass
class NestedBlock:
    block: Block
    nesting: NestingMode
    min_items: int = 0
    max_items: int = 0


def encode_type(obj: typing.Any) -> bytes:
    return json.dumps(obj, separators=(",", ":")).encode("ascii")


class Schema(marshmallow.Schema):
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
                    type=encode_type(field.get_terraform_type()),
                    description=field.metadata["description"],
                    required=field.required,
                    optional=field.metadata["optional"],
                    computed=field.metadata["computed"],
                    sensitive=field.metadata["sensitive"],
                )
                continue

        return Block(attributes=attributes, block_types=block_types)


class Resource(Schema):
    ...
