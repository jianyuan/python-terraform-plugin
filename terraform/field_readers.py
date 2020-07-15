import abc
import dataclasses
import typing

from terraform import diffs, fields, resources, schemas


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
class ConfigFieldReader(BaseFieldReader):
    config: resources.ResourceConfig
    schema: schemas.Schema

    def get(self, path: typing.Sequence[typing.Any]) -> FieldReadResult:
        key = ".".join(path)
        schema_list = self.schema.get_by_path(path)
        if not schema_list:
            return FieldReadResult()

        schema = schema_list[-1]

        if isinstance(schema, fields.BaseField) and schema.primitive:
            try:
                value = self.config[key]
            except KeyError:
                return FieldReadResult()

            computed = False  # determine computed
            return FieldReadResult(value=value, exists=True, computed=computed)

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
            # TODO: check both the raw value and the interpolated
            result = {}
            computed = False

            value = self.config.get(key)

            if isinstance(value, str):
                raise NotImplementedError

            elif isinstance(value, typing.Sequence):
                raise NotImplementedError

            elif isinstance(value, typing.Mapping):
                for this_key_part in value:
                    this_key = f"{key}.{this_key_part}"

                    if self.config.is_computed(key):
                        computed = True
                        break

                    result[this_key_part] = self.config.get(this_key)
            else:
                raise NotImplementedError

            return FieldReadResult(
                value=None if computed else result, exists=True, computed=computed
            )

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
                source_result = self.source.get(path)
                if source_result.exists:
                    return source_result

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
