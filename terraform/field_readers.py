import abc
import dataclasses
import typing

from terraform import diffs, fields, schemas


@dataclasses.dataclass
class FieldReadResult:
    value: typing.Any = None
    value_processed: typing.Any = None  # NOTE: unused
    exists: bool = False
    computed: bool = False


class BaseFieldReader(abc.ABC):
    @abc.abstractmethod
    def get(self, path: typing.Sequence[typing.Any]) -> FieldReadResult:
        ...


@dataclasses.dataclass
class DictFieldReader(BaseFieldReader):
    data: typing.Dict[typing.Any, typing.Any]

    def get(self, path: typing.Sequence[typing.Any]) -> FieldReadResult:
        try:
            value = self.data
            for part in path:
                value = value[part]
            return FieldReadResult(value=value, exists=True)
        except KeyError:
            return FieldReadResult()


@dataclasses.dataclass
class DiffFieldReader(BaseFieldReader):
    diff: diffs.InstanceDiff
    source: BaseFieldReader
    schema: schemas.Schema

    def get(self, path: typing.Sequence[typing.Any]) -> FieldReadResult:
        schema_list = self.schema.get_by_path(path)
        if not schema_list:
            return FieldReadResult()

        schema = schema_list[-1]

        if isinstance(schema, fields.BaseField) and schema.primitive:
            result = self.source.get(path)

            try:
                diff_attribute = self.diff.attributes[".".join(path)]
            except KeyError:
                return FieldReadResult()

            result.computed = diff_attribute.new_computed
            result.exists = True
            result.value = diff_attribute.new

            return result

        elif isinstance(schema, fields.Set):
            result = []

            prefix = ".".join(path) + "."
            indexes = []
            for raw_key, raw_value in self.diff.attributes.items():
                if raw_value.new_removed:
                    continue

                if not raw_key.startswith(prefix):
                    continue

                if raw_key.endswith("#"):
                    continue

                parts = raw_key[len(prefix) :].split(".")
                index = parts[0]
                if index not in indexes:
                    indexes.append(index)

            for index in indexes:
                value = self.get(path + [index])
                assert value.exists
                result.append(value.value)

            result_exists = len(result) > 0 or prefix + "#" in self.diff.attributes

            if not result_exists:
                result = self.source.get(path)
                if result.exists:
                    return result

            return FieldReadResult(value=result, exists=result_exists)

        elif isinstance(schema, fields.List):
            count_result = self.get(path + ["#"])
            if not count_result.exists:
                count_result.value = 0

            if count_result.computed or count_result.value == 0:
                return FieldReadResult(
                    value=[], exists=count_result.exists, computed=count_result.computed
                )

            result = []
            for i in range(count_result.value):
                item_result = self.get(path + [str(i)])
                result.append(item_result.value)

            return FieldReadResult(value=result, exists=True)

        elif isinstance(schema, fields.Map):
            result = {}
            result_exists = False

            source = self.source.get(path)
            if source.exists:
                result = source.value
                result_exists = True

            prefix = ".".join(path) + "."
            for raw_key, value in self.diff.attributes.items():
                if not raw_key.startswith(prefix):
                    continue

                if raw_key.startswith(prefix + "%"):
                    continue

                result_exists = True

                key = raw_key[len(prefix) :]
                if value.new_removed:
                    if key in result:
                        del result[key]
                    continue

                result[key] = value.new

            return FieldReadResult(value=result, exists=result_exists)

        elif isinstance(schema, schemas.Schema):
            result = {}
            result_exists = False

            for field in schema.declared_fields:
                raw_value = self.get(path + [field])
                if raw_value.exists:
                    result_exists = True

                result[field] = raw_value.value

            return FieldReadResult(value=result, exists=result_exists)

        else:
            raise NotImplementedError

    # def get2(self, path: typing.Sequence[typing.Any]) -> FieldReadResult:
    #     schema_or_field = self.schema
    #     diff = self.diff.attributes
    #     source = self.source.get(path)

    #     for part in path:
    #         if isinstance(schema_or_field, schemas.Schema):
    #             schema_or_field = schema_or_field.declared_fields.get(part)
    #             if schema_or_field is None:
    #                 diff = None
    #                 break

    #             elif isinstance(schema_or_field, fields.BaseField):
    #                 if schema_or_field.primitive:
    #                     diff = diff.get(schema_or_field.name)
    #                 elif isinstance(schema_or_field, fields.List):
    #                     diff = diff.get(schema_or_field.name)
    #                 elif isinstance(schema_or_field, fields.Map):
    #                     diff = diff.get(schema_or_field.name)
    #                 else:
    #                     raise NotImplementedError

    #             else:
    #                 raise NotImplementedError

    #         else:
    #             raise NotImplementedError

    #     if diff is None:
    #         return FieldReadResult()

    #     elif schema_or_field.primitive:
    #         return FieldReadResult(
    #             value=diff.new, exists=True, computed=diff.new_computed
    #         )

    #     elif isinstance(schema_or_field, fields.List):
    #         schema_diff = diff.get(diffs.SCHEMA)
    #         if schema_diff is None or schema_diff.new_computed or schema_diff.new == 0:
    #             return FieldReadResult(
    #                 result=[], exists=True, computed=schema_diff.new_computed
    #             )

    #         result = []

    #         if isinstance(schema_or_field, fields.Set):
    #             for k, v in diff.items():
    #                 if k == diffs.SCHEMA:
    #                     continue
    #                 result.append(v.new)
    #         else:
    #             for i in range(schema_diff.new):
    #                 if i in diff:
    #                     result.append(diff[i].new)
    #                 else:
    #                     result.append(None)

    #         return FieldReadResult(value=result, exists=True)

    #     elif isinstance(schema_or_field, fields.Map):
    #         if source.exists:
    #             result = source.value.copy()
    #             exists = True
    #         else:
    #             result = {}
    #             exists = False

    #         for k, v in diff.items():
    #             exists = True

    #             if v.new_removed:
    #                 if k in result:
    #                     del result[k]
    #                 continue

    #             result[k] = v.new

    #         return FieldReadResult(value=result, exists=exists)

    #     else:
    #         raise NotImplementedError
