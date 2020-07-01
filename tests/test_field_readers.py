import pytest

from terraform import diffs, field_readers, fields, schemas


class FieldReaderSchema_Nested(schemas.Schema):
    index = fields.Int()
    value = fields.String()


class FieldReaderSchema(schemas.Schema):
    bool = fields.Bool()
    float = fields.Float()
    int = fields.Int()
    string = fields.String()

    list = fields.List(fields.String())
    list_int = fields.List(fields.Int())
    list_map = fields.List(fields.Map())

    map = fields.Map()
    map_int = fields.Map(fields.Int())
    map_int_nested_schema = fields.Map(fields.Nested(fields.Int()))
    map_float = fields.Map(fields.Float())
    map_bool = fields.Map(fields.Bool())

    set = fields.Set(fields.Int())
    set_deep = fields.Set(fields.Nested(FieldReaderSchema_Nested()))
    set_empty = fields.Set(fields.Int())


@pytest.mark.parametrize(
    "path,expected",
    [
        (
            ["boolNOPE"],
            field_readers.FieldReadResult(value=None, exists=False, computed=False),
        ),
        (
            ["bool"],
            field_readers.FieldReadResult(value=True, exists=True, computed=False),
        ),
        (
            ["float"],
            field_readers.FieldReadResult(value=3.1415, exists=True, computed=False),
        ),
        (
            ["int"],
            field_readers.FieldReadResult(value=42, exists=True, computed=False),
        ),
        (
            ["string"],
            field_readers.FieldReadResult(value="string", exists=True, computed=False),
        ),
        (
            ["list"],
            field_readers.FieldReadResult(
                value=["foo", "bar"], exists=True, computed=False
            ),
        ),
        (
            ["list_int"],
            field_readers.FieldReadResult(value=[21, 42], exists=True, computed=False),
        ),
        (
            ["map"],
            field_readers.FieldReadResult(
                value={"foo": "bar", "bar": "baz"}, exists=True, computed=False
            ),
        ),
        (
            ["map_int"],
            field_readers.FieldReadResult(
                value={"one": 1, "two": 2}, exists=True, computed=False
            ),
        ),
        (
            ["map_int_nested_schema"],
            field_readers.FieldReadResult(
                value={"one": 1, "two": 2}, exists=True, computed=False
            ),
        ),
        (
            ["map_float"],
            field_readers.FieldReadResult(
                value={"one_dot_two": 1.2}, exists=True, computed=False
            ),
        ),
        (
            ["map_bool"],
            field_readers.FieldReadResult(
                value={"True": True, "False": False}, exists=True, computed=False
            ),
        ),
        (
            ["map", "foo"],
            field_readers.FieldReadResult(value="bar", exists=True, computed=False),
        ),
        (
            ["set"],
            field_readers.FieldReadResult(value=[10, 50], exists=True, computed=False),
        ),
        (
            ["set_deep"],
            field_readers.FieldReadResult(
                value=[{"index": 10, "value": "foo"}, {"index": 50, "value": "bar"}],
                exists=True,
                computed=False,
            ),
        ),
        # (
        #     ["set_empty"],
        #     field_readers.FieldReadResult(value=[], exists=False, computed=False),
        # ),
    ],
)
def test_diff_field_reader(path, expected):
    reader = field_readers.DiffFieldReader(
        diff=diffs.InstanceDiff(
            attributes={
                "bool": diffs.AttributeDiff(old=None, new=True),
                "int": diffs.AttributeDiff(old=None, new=42),
                "float": diffs.AttributeDiff(old=None, new=3.1415),
                "string": diffs.AttributeDiff(old=None, new="string"),
                "string_computed": diffs.AttributeDiff(
                    old="foo", new="bar", new_computed=True
                ),
                "list.#": diffs.AttributeDiff(old=0, new=2),
                "list.0": diffs.AttributeDiff(old=None, new="foo"),
                "list.1": diffs.AttributeDiff(old=None, new="bar"),
                "list_int.#": diffs.AttributeDiff(old=0, new=2),
                "list_int.0": diffs.AttributeDiff(old=None, new=21),
                "list_int.1": diffs.AttributeDiff(old=None, new=42),
                "map.foo": diffs.AttributeDiff(old=None, new="bar"),
                "map.bar": diffs.AttributeDiff(old=None, new="baz"),
                "map_int.%": diffs.AttributeDiff(old=None, new=2),
                "map_int.one": diffs.AttributeDiff(old=None, new=1),
                "map_int.two": diffs.AttributeDiff(old=None, new=2),
                "map_int_nested_schema.%": diffs.AttributeDiff(old=None, new=2),
                "map_int_nested_schema.one": diffs.AttributeDiff(old=None, new=1),
                "map_int_nested_schema.two": diffs.AttributeDiff(old=None, new=2),
                "map_float.%": diffs.AttributeDiff(old=None, new=1),
                "map_float.one_dot_two": diffs.AttributeDiff(old=None, new=1.2),
                "map_bool.%": diffs.AttributeDiff(old=None, new=2),
                "map_bool.True": diffs.AttributeDiff(old=None, new=True),
                "map_bool.False": diffs.AttributeDiff(old=None, new=False),
                "set.#": diffs.AttributeDiff(old=0, new=2),
                "set.10": diffs.AttributeDiff(old=None, new=10),
                "set.50": diffs.AttributeDiff(old=None, new=50),
                "set_deep.#": diffs.AttributeDiff(old=0, new=2),
                "set_deep.10.index": diffs.AttributeDiff(old=None, new=10),
                "set_deep.10.value": diffs.AttributeDiff(old=None, new="foo"),
                "set_deep.50.index": diffs.AttributeDiff(old=None, new=50),
                "set_deep.50.value": diffs.AttributeDiff(old=None, new="bar"),
            }
        ),
        source=field_readers.DictFieldReader(
            {"list_map": [{"foo": "bar", "bar": "baz"}, {"baz": "baz"}]}
        ),
        schema=FieldReaderSchema(),
    )
    assert reader.get(path) == expected
