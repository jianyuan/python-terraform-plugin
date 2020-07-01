import pytest

from terraform import field_writers, fields, schemas


@pytest.mark.parametrize(
    "path,value,exception,expected",
    [
        (["noexist"], 42, KeyError, {}),
        (["bool"], False, None, {"bool": False}),
        (["int"], 42, None, {"int": 42}),
        (["string"], "42", None, {"string": "42"}),
        pytest.param(["string"], None, None, {"string": None}, id="string nil"),
        pytest.param(
            ["list_resource"],
            [{"value": 80}],
            None,
            {"list_resource.#": 1, "list_resource.0.value": 80},
            id="list of resources",
        ),
        pytest.param(
            ["list_resource"],
            [],
            None,
            {"list_resource.#": 0},
            id="list of resources empty",
        ),
        pytest.param(
            ["list_resource"],
            None,
            None,
            {"list_resource.#": 0},
            id="list of resources none",
        ),
        pytest.param(
            ["list"],
            ["foo", "bar"],
            None,
            {"list.#": 2, "list.0": "foo", "list.1": "bar"},
            id="list of strings",
        ),
        pytest.param(["list", "0"], ["string"], ValueError, {}, id="list element"),
        pytest.param(["map"], {"foo": "bar"}, None, {"map.%": 1, "map.foo": "bar"}),
        pytest.param(["map"], None, None, {"map": None}, id="map delete"),
        pytest.param(["map", "foo"], "bar", ValueError, {}, id="map element"),
        pytest.param(
            ["set"], [1, 2, 5], None, {"set.#": 3, "set.0": 1, "set.1": 2, "set.2": 5},
        ),
        pytest.param(["set"], None, None, {"set.#": 0}, id="set none"),
        pytest.param(
            ["set_deep"],
            [{"index": 10, "value": "foo"}, {"index": 50, "value": "bar"}],
            None,
            {
                "set_deep.#": 2,
                "set_deep.0.index": 10,
                "set_deep.0.value": "foo",
                "set_deep.1.index": 50,
                "set_deep.1.value": "bar",
            },
            id="set deep",
        ),
        pytest.param(["set", "5"], 5, ValueError, {}, id="set element"),
        pytest.param(
            None,
            {"string": "foo", "list": ["foo", "bar"]},
            None,
            {"string": "foo", "list.#": 2, "list.0": "foo", "list.1": "bar"},
            id="full object",
        ),
    ],
)
def test_field_writer(path, value, exception, expected):
    class TestSchema(schemas.Schema):
        bool = fields.Bool()
        int = fields.Int()
        string = fields.String()
        list = fields.List(fields.String())
        list_int = fields.List(fields.Int())
        list_resource = fields.List(
            fields.Nested(
                schemas.Schema.from_dict({"value": fields.Int(optional=True)})
            )
        )
        map = fields.Map()
        set = fields.Set(fields.Int())
        set_deep = fields.Set(
            fields.Nested(
                schemas.Schema.from_dict(
                    {"index": fields.Int(), "value": fields.String()}
                )
            )
        )

    writer = field_writers.FieldWriter(schema=TestSchema())
    if exception is None:
        writer.write_field(path, value)
    else:
        with pytest.raises(exception):
            writer.write_field(path, value)

    assert writer.data == expected


def test_field_writer_clean_set():
    class TestSchema(schemas.Schema):
        set_deep = fields.Set(
            fields.Nested(
                schemas.Schema.from_dict(
                    {"index": fields.Int(), "value": fields.String()}
                )
            )
        )

    writer = field_writers.FieldWriter(schema=TestSchema())

    actions = [
        # Base set
        (
            ["set_deep"],
            [{"index": 10, "value": "foo"}, {"index": 50, "value": "bar"}],
            {
                "set_deep.#": 2,
                "set_deep.0.index": 10,
                "set_deep.0.value": "foo",
                "set_deep.1.index": 50,
                "set_deep.1.value": "bar",
            },
        ),
        (
            ["set_deep"],
            [{"index": 20, "value": "baz"}, {"index": 60, "value": "qux"}],
            {
                "set_deep.#": 2,
                "set_deep.0.index": 20,
                "set_deep.0.value": "baz",
                "set_deep.1.index": 60,
                "set_deep.1.value": "qux",
            },
        ),
        (
            ["set_deep"],
            [{"index": 30, "value": "one"}, {"index": 70, "value": "two"}],
            {
                "set_deep.#": 2,
                "set_deep.0.index": 30,
                "set_deep.0.value": "one",
                "set_deep.1.index": 70,
                "set_deep.1.value": "two",
            },
        ),
    ]

    for path, value, expected in actions:
        writer.write_field(path, value)
        assert writer.data == expected


def test_field_writer_clean_list():
    class TestSchema(schemas.Schema):
        list_deep = fields.List(
            fields.Nested(
                schemas.Schema.from_dict(
                    {"thing1": fields.String(), "thing2": fields.String()}
                )
            )
        )

    writer = field_writers.FieldWriter(schema=TestSchema())

    actions = [
        # Base list
        (
            ["list_deep"],
            [
                {"thing1": "a", "thing2": "b"},
                {"thing1": "c", "thing2": "d"},
                {"thing1": "e", "thing2": "f"},
                {"thing1": "g", "thing2": "h"},
            ],
            {
                "list_deep.#": 4,
                "list_deep.0.thing1": "a",
                "list_deep.0.thing2": "b",
                "list_deep.1.thing1": "c",
                "list_deep.1.thing2": "d",
                "list_deep.2.thing1": "e",
                "list_deep.2.thing2": "f",
                "list_deep.3.thing1": "g",
                "list_deep.3.thing2": "h",
            },
        ),
        # Remove an element
        (
            ["list_deep"],
            [
                {"thing1": "a", "thing2": "b"},
                {"thing1": "c", "thing2": "d"},
                {"thing1": "e", "thing2": "f"},
            ],
            {
                "list_deep.#": 3,
                "list_deep.0.thing1": "a",
                "list_deep.0.thing2": "b",
                "list_deep.1.thing1": "c",
                "list_deep.1.thing2": "d",
                "list_deep.2.thing1": "e",
                "list_deep.2.thing2": "f",
            },
        ),
        # Rewrite with missing keys
        (
            ["list_deep"],
            [{"thing1": "a"}, {"thing1": "c"}, {"thing1": "e"}],
            {
                "list_deep.#": 3,
                "list_deep.0.thing1": "a",
                "list_deep.1.thing1": "c",
                "list_deep.2.thing1": "e",
            },
        ),
    ]

    for path, value, expected in actions:
        writer.write_field(path, value)
        assert writer.data == expected


def test_field_writer_clean_map():
    class TestSchema(schemas.Schema):
        map = fields.Map()

    writer = field_writers.FieldWriter(schema=TestSchema())

    actions = [
        # Base map
        (
            {"thing1": "a", "thing2": "b", "thing3": "c", "thing4": "d"},
            {
                "map.%": 4,
                "map.thing1": "a",
                "map.thing2": "b",
                "map.thing3": "c",
                "map.thing4": "d",
            },
        ),
        (
            {"thing1": "a", "thing2": "b", "thing4": "d"},
            {"map.%": 3, "map.thing1": "a", "map.thing2": "b", "map.thing4": "d"},
        ),
    ]

    for value, expected in actions:
        writer.write_field(["map"], value)
        assert writer.data == expected
