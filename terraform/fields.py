import typing

import marshmallow


class BaseField(marshmallow.fields.Field):
    primitive: bool = False
    terraform_type: typing.Optional[str] = None

    def __init__(
        self,
        *,
        default: typing.Any = None,
        allow_none: bool = True,
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
        super().__init__(default=default, allow_none=allow_none, **kwargs, **metadata)

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

    def get_inner(self):
        raise NotImplementedError

    def get_terraform_type(self) -> typing.Any:
        return [self.terraform_type, self.get_inner().get_terraform_type()]


class Bool(marshmallow.fields.Boolean, BaseField):
    primitive = True
    terraform_type = "bool"


class Int(marshmallow.fields.Integer, BaseField):
    primitive = True
    terraform_type = "number"


class Float(marshmallow.fields.Float, BaseField):
    primitive = True
    terraform_type = "number"


class String(marshmallow.fields.String, BaseField):
    primitive = True
    terraform_type = "string"


class List(marshmallow.fields.List, BaseNestedField):
    terraform_type = "list"

    def get_inner(self):
        return self.inner


class Set(List, BaseNestedField):
    terraform_type = "set"


class Map(marshmallow.fields.Mapping, BaseNestedField):
    terraform_type = "map"

    def __init__(self, values=None, **kwargs):
        if values is None:
            values = String()
        super().__init__(String(), values, **kwargs)

    def get_inner(self):
        from terraform import schemas

        if isinstance(self.value_field, Nested) and isinstance(
            self.value_field.nested, schemas.Resource
        ):
            return String()
        return self.value_field


class Nested(marshmallow.fields.Nested, BaseField):
    def get_terraform_type(self) -> typing.Any:
        return self.nested.get_terraform_type()
