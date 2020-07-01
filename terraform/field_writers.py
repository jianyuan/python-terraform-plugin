import dataclasses
import typing

from terraform import fields, schemas


@dataclasses.dataclass
class FieldWriter:
    schema: schemas.Schema
    data: typing.Dict[str, typing.Any] = dataclasses.field(
        init=False, default_factory=dict
    )

    def write_field(
        self, path: typing.Optional[typing.Sequence[str]], value: typing.Any
    ):
        if path is None:
            path = []

        schema_list = self.schema.get_by_path(path)
        if not schema_list:
            raise KeyError(path)

        for schema in schema_list[:-1]:
            if isinstance(schema, (fields.List, fields.Map)):
                raise ValueError(f"can only set full {schema.terraform_type}")

        self._set(path=path, schema_list=schema_list, value=value)

    def _set(self, *, path, value, schema_list=None):
        full_path = ".".join(path)

        if schema_list is None:
            schema_list = self.schema.get_by_path(path)
        schema = schema_list[-1]

        if isinstance(schema, fields.BaseField) and schema.primitive:
            if value is not None and not isinstance(value, schema.python_type):
                raise TypeError(f"value must be of type: {schema.python_type}")
            self.data[full_path] = value

        elif isinstance(schema, fields.List):
            self._clear_tree(path=path)

            if value is None:
                self.data[full_path + ".#"] = 0
            else:
                for i, v in enumerate(value):
                    self._set(path=path + [str(i)], value=v)
                self.data[full_path + ".#"] = len(value)

        elif isinstance(schema, fields.Map):
            self._clear_tree(path=path)

            if value is None:
                self.data[full_path] = None
            else:
                for k, v in value.items():
                    self._set(path=path + [k], value=v)
                self.data[full_path + ".%"] = len(value)

        elif isinstance(schema, schemas.Schema):
            for k, v in value.items():
                # TODO: Calculate hashcode
                self._set(path=path + [k], value=v)

        else:
            raise NotImplementedError

    def _clear_tree(self, *, path):
        prefix = ".".join(path) + "."
        for k in list(self.data.keys()):
            if k.startswith(prefix):
                del self.data[k]
