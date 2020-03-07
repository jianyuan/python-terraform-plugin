import typing

import marshmallow


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
        removed: typing.Optional[str] = None,
        deprecated: typing.Optional[str] = None,
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
            "removed": removed,
            "deprecated": deprecated,
        }
        kwargs.setdefault("allow_none", True)
        super().__init__(**kwargs, **metadata)

    def get_terraform_type(self) -> typing.Any:
        if self.terraform_type is not None:
            return self.terraform_type
        raise NotImplementedError

    def serialize(self, *args, **kwargs):
        if (
            self.metadata["removed"] is not None
            or self.metadata["deprecated"] is not None
        ):
            return None
        return super().serialize(*args, **kwargs)


class BaseNestedField(BaseField):
    def __init__(
        self, min_items: int = 0, max_items: int = 0, **kwargs,
    ):
        # TODO: validate metadata
        metadata = {
            "min_items": min_items,
            "max_items": max_items,
        }
        super().__init__(**kwargs, **metadata)


class Bool(marshmallow.fields.Boolean, BaseField):
    terraform_type = "bool"


class Int(marshmallow.fields.Integer, BaseField):
    terraform_type = "number"


class Float(marshmallow.fields.Float, BaseField):
    terraform_type = "number"


class String(marshmallow.fields.String, BaseField):
    terraform_type = "string"


class List(marshmallow.fields.List, BaseNestedField):
    def get_terraform_type(self) -> typing.Any:
        return ["list", self.inner.get_terraform_type()]


class Map(marshmallow.fields.Mapping, BaseNestedField):
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


class Set(marshmallow.fields.List, BaseNestedField):
    def get_terraform_type(self) -> typing.Any:
        return ["set", self.inner.get_terraform_type()]


class Nested(marshmallow.fields.Nested, BaseField):
    def get_terraform_type(self) -> typing.Any:
        return self.nested.get_terraform_type()
