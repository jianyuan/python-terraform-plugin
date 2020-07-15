import pytest

from terraform import fields, resources, schemas

foo_string_schema = schemas.Schema.from_dict({"foo": fields.String(optional=True)})

foo_list_schema = schemas.Schema.from_dict(
    {"foo": fields.List(fields.Int(), optional=True)}
)


@pytest.mark.parametrize(
    "config,schema,key,value",
    [
        ({"foo": "bar"}, foo_string_schema, "foo", "bar"),
        ({"foo": fields.missing}, foo_string_schema, "foo", fields.missing),
        ({"foo": [1, 2, 5]}, foo_list_schema, "foo.0", 1),
        ({"foo": [1, 2, 5]}, foo_list_schema, "foo.#", 3),
        ({"foo": [fields.missing, 2, 5]}, foo_list_schema, "foo.#", fields.missing),
        ({"foo": [1, 2, 5]}, foo_list_schema, "foo.5", KeyError),
        ({"foo": [1, 2, 5]}, foo_list_schema, "foo.-1", KeyError),
        # get from map
        (
            {"mapname": [{"key": 1}]},
            schemas.Schema.from_dict(
                {"mapname": fields.List(fields.Map(fields.Int()), optional=True)}
            ),
            "mapname.0.key",
            1,
        ),
        # get from map with dot in key
        (
            {"mapname": [{"key.name": 1}]},
            schemas.Schema.from_dict(
                {"mapname": fields.List(fields.Map(fields.Int()), optional=True)}
            ),
            "mapname.0.key.name",
            1,
        ),
        # get from map with overlapping key names
        (
            {"mapname": [{"key.name": 1, "key.name.2": 2}]},
            schemas.Schema.from_dict(
                {"mapname": fields.List(fields.Map(fields.Int()), optional=True)}
            ),
            "mapname.0.key.name.2",
            2,
        ),
        (
            {"mapname": [{"key.name": 1, "key.name.foo": 2}]},
            schemas.Schema.from_dict(
                {"mapname": fields.List(fields.Map(fields.Int()), optional=True)}
            ),
            "mapname.0.key.name",
            1,
        ),
        (
            {"mapname": [{"listkey": [{"key": 3}]}]},
            schemas.Schema.from_dict(
                {
                    "mapname": fields.List(
                        fields.Map(fields.List(fields.Map(fields.Int()))), optional=True
                    )
                }
            ),
            "mapname.0.listkey.0.key",
            3,
        ),
    ],
)
def test_resource_config_get(config, schema, key, value):
    resource_config = resources.ResourceConfig(schema=schema, config=config)

    if isinstance(value, type) and issubclass(value, Exception):
        with pytest.raises(value):
            assert resource_config[key] is None
    else:
        assert resource_config[key] == value


@pytest.mark.parametrize(
    "input,result",
    [
        pytest.param(42, False, id="primitive"),
        pytest.param(fields.missing, True, id="primitive computed"),
        pytest.param(["foo", fields.missing], True, id="list"),
        pytest.param(["foo", [fields.missing]], True, id="nested list"),
        pytest.param({"foo": 1, "bar": 2}, False, id="map"),
        pytest.param({"foo": 1, "bar": fields.missing}, True, id="map computed"),
        pytest.param(
            {"foo": 1, "bar": [2, fields.missing]}, True, id="map list computed"
        ),
    ],
)
def test_has_missing(input, result):
    assert resources.has_missing(input) == result
