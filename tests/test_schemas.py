import itertools
import typing

import pytest

from terraform import fields, schemas
from terraform.protos import tfplugin5_1_pb2


class NestedAttributesAndBlocks_Resource(schemas.Resource):
    bar = fields.List(
        fields.Nested(fields.List(fields.Nested(fields.String()))), required=True,
    )
    baz = fields.Set(fields.Nested(schemas.Resource()), optional=True)


class NestedAttributesAndBlocksSchema(schemas.Schema):
    foo = fields.List(
        fields.Nested(NestedAttributesAndBlocks_Resource()), required=True
    )


def conditionally_required_error_schema_missing():
    raise ValueError


class ConditionallyRequiredErrorSchema(schemas.Schema):
    string = fields.String(
        required=True, default=conditionally_required_error_schema_missing
    )


ID_ATTRIBUTE = schemas.Attribute(type="string", optional=True, computed=True)


@pytest.mark.parametrize(
    "subject,want",
    [
        pytest.param(schemas.Schema(), schemas.Block(), id="empty"),
        pytest.param(
            schemas.Schema.from_dict(
                {
                    "int": fields.Int(
                        name="int", required=True, description="foo bar baz"
                    ),
                    "float": fields.Float(name="float", optional=True),
                    "bool": fields.Bool(name="bool", computed=True),
                    "string": fields.String(optional=True, computed=True),
                }
            )(),
            schemas.Block(
                attributes={
                    "int": schemas.Attribute(
                        type="number", required=True, description="foo bar baz",
                    ),
                    "float": schemas.Attribute(type="number", optional=True),
                    "bool": schemas.Attribute(type="bool", computed=True),
                    "string": schemas.Attribute(
                        type="string", optional=True, computed=True,
                    ),
                },
            ),
            id="primitives",
        ),
        pytest.param(
            schemas.Schema.from_dict(
                {
                    "list": fields.List(fields.Int(), required=True),
                    "set": fields.Set(fields.String(), optional=True),
                    "map": fields.Map(fields.Bool(), optional=True),
                    "map_default_type": fields.Map(optional=True),
                }
            )(),
            schemas.Block(
                attributes={
                    "list": schemas.Attribute(type=["list", "number"], required=True),
                    "set": schemas.Attribute(type=["set", "string"], optional=True),
                    "map": schemas.Attribute(type=["map", "bool"], optional=True),
                    "map_default_type": schemas.Attribute(
                        type=["map", "string"], optional=True,
                    ),
                },
            ),
            id="simple collections",
        ),
        pytest.param(
            schemas.Schema.from_dict(
                {
                    "list": fields.List(fields.Int(), required=True),
                    "set": fields.Set(fields.String(), optional=True),
                    "map": fields.Map(fields.Bool(), optional=True),
                }
            )(),
            schemas.Block(
                attributes={
                    "list": schemas.Attribute(type=["list", "number"], required=True),
                    "set": schemas.Attribute(type=["set", "string"], optional=True),
                    "map": schemas.Attribute(type=["map", "bool"], optional=True),
                }
            ),
            id="incorrectly-specified collections",
        ),
        pytest.param(
            schemas.Schema.from_dict(
                {
                    "list": fields.List(
                        fields.Nested(schemas.Resource()),
                        required=True,
                        min_items=1,
                        max_items=2,
                    ),
                    "set": fields.Set(fields.Nested(schemas.Resource()), required=True),
                    "map": fields.Map(fields.Nested(schemas.Resource()), optional=True),
                }
            )(),
            schemas.Block(
                attributes={
                    "map": schemas.Attribute(type=["map", "string"], optional=True),
                },
                block_types={
                    "list": schemas.NestedBlock(
                        nesting=schemas.NestingMode.LIST,
                        block=schemas.Block(attributes={"id": ID_ATTRIBUTE}),
                        min_items=1,
                        max_items=2,
                    ),
                    "set": schemas.NestedBlock(
                        nesting=schemas.NestingMode.SET,
                        block=schemas.Block(attributes={"id": ID_ATTRIBUTE}),
                        min_items=1,
                    ),
                },
            ),
            id="sub-resource collections",
        ),
        pytest.param(
            schemas.Schema.from_dict(
                {
                    "list": fields.List(
                        fields.Nested(schemas.Resource()),
                        optional=True,
                        min_items=1,
                        max_items=1,
                    ),
                    "set": fields.Set(
                        fields.Nested(schemas.Resource()),
                        optional=True,
                        min_items=1,
                        max_items=1,
                    ),
                }
            )(),
            schemas.Block(
                block_types={
                    "list": schemas.NestedBlock(
                        nesting=schemas.NestingMode.LIST,
                        block=schemas.Block(attributes={"id": ID_ATTRIBUTE}),
                        min_items=0,
                        max_items=1,
                    ),
                    "set": schemas.NestedBlock(
                        nesting=schemas.NestingMode.SET,
                        block=schemas.Block(attributes={"id": ID_ATTRIBUTE}),
                        min_items=0,
                        max_items=1,
                    ),
                }
            ),
            id="sub-resource collections minitems+optional",
        ),
        pytest.param(
            schemas.Schema.from_dict(
                {
                    "list": fields.List(
                        fields.Nested(schemas.Resource()),
                        computed=True,
                        min_items=1,
                        max_items=1,
                    ),
                    "set": fields.Set(
                        fields.Nested(schemas.Resource()),
                        computed=True,
                        min_items=1,
                        max_items=1,
                    ),
                }
            )(),
            schemas.Block(
                attributes={
                    "list": schemas.Attribute(
                        type=["list", ["object", {"id": "string"}]], computed=True,
                    ),
                    "set": schemas.Attribute(
                        type=["set", ["object", {"id": "string"}]], computed=True,
                    ),
                }
            ),
            id="sub-resource collections minitems+computed",
        ),
        pytest.param(
            NestedAttributesAndBlocksSchema(),
            schemas.Block(
                block_types={
                    "foo": schemas.NestedBlock(
                        nesting=schemas.NestingMode.LIST,
                        block=schemas.Block(
                            attributes={
                                "id": ID_ATTRIBUTE,
                                "bar": schemas.Attribute(
                                    type=["list", ["list", "string"]], required=True,
                                ),
                            },
                            block_types={
                                "baz": schemas.NestedBlock(
                                    nesting=schemas.NestingMode.SET,
                                    block=schemas.Block(
                                        attributes={"id": ID_ATTRIBUTE}
                                    ),
                                )
                            },
                        ),
                        min_items=1,
                    )
                }
            ),
            id="nested attributes and blocks",
        ),
        pytest.param(
            schemas.Schema.from_dict(
                {"string": fields.String(optional=True, sensitive=True)}
            )(),
            schemas.Block(
                attributes={
                    "string": schemas.Attribute(
                        type="string", optional=True, sensitive=True
                    )
                }
            ),
            id="sensitive",
        ),
        pytest.param(
            schemas.Schema.from_dict(
                {"string": fields.String(required=True, default=lambda: None)}
            )(),
            schemas.Block(
                attributes={"string": schemas.Attribute(type="string", required=True)}
            ),
            id="conditionally required on",
        ),
        pytest.param(
            schemas.Schema.from_dict(
                {"string": fields.String(required=True, default=lambda: "boop")}
            )(),
            schemas.Block(
                attributes={"string": schemas.Attribute(type="string", optional=True)}
            ),
            id="conditionally required off",
        ),
        pytest.param(
            ConditionallyRequiredErrorSchema(),
            schemas.Block(
                attributes={"string": schemas.Attribute(type="string", optional=True)}
            ),
            id="conditionally required error",
        ),
    ],
)
def test_schema(subject: schemas.Schema, want: schemas.Block):
    assert subject.to_block() == want


@pytest.mark.parametrize(
    "subject,path,want",
    [
        pytest.param(
            schemas.Schema.from_dict({"list": fields.List(fields.Int())})(),
            [],
            [schemas.Schema],
            id="full object",
        ),
        pytest.param(
            schemas.Schema.from_dict({"list": fields.List(fields.Int())})(),
            ["list"],
            [fields.List],
            id="list",
        ),
        pytest.param(
            schemas.Schema.from_dict({"list": fields.List(fields.Int())})(),
            ["list", "#"],
            [fields.List, fields.Int],
            id="list.#",
        ),
        pytest.param(
            schemas.Schema.from_dict({"list": fields.List(fields.Int())})(),
            ["list", "0"],
            [fields.List, fields.Int],
            id="list.0",
        ),
        pytest.param(
            schemas.Schema.from_dict(
                {
                    "list": fields.List(
                        fields.Nested(
                            schemas.Schema.from_dict({"field": fields.String()})
                        )
                    )
                }
            )(),
            ["list", "0"],
            [fields.List, schemas.Schema],
            id="list.0 with resource",
        ),
        pytest.param(
            schemas.Schema.from_dict(
                {
                    "list": fields.List(
                        fields.Nested(
                            schemas.Schema.from_dict({"field": fields.String()})
                        )
                    )
                }
            )(),
            ["list", "0", "field"],
            [fields.List, schemas.Schema, fields.String],
            id="list.0.field",
        ),
        pytest.param(
            schemas.Schema.from_dict({"set": fields.Set(fields.Int())})(),
            ["set"],
            [fields.Set],
            id="set",
        ),
        pytest.param(
            schemas.Schema.from_dict({"set": fields.Set(fields.Int())})(),
            ["set", "#"],
            [fields.Set, fields.Int],
            id="set.#",
        ),
        pytest.param(
            schemas.Schema.from_dict({"set": fields.Set(fields.Int())})(),
            ["set", "0"],
            [fields.Set, fields.Int],
            id="set.0",
        ),
        pytest.param(
            schemas.Schema.from_dict(
                {
                    "set": fields.Set(
                        fields.Nested(
                            schemas.Schema.from_dict({"field": fields.String()})
                        )
                    )
                }
            )(),
            ["set", "0"],
            [fields.Set, schemas.Schema],
            id="set.0 with resource",
        ),
        pytest.param(
            schemas.Schema.from_dict({"map": fields.Map()})(),
            ["map", "foo"],
            [fields.Map, fields.String],
            id="map_elem",
        ),
        pytest.param(
            schemas.Schema.from_dict(
                {
                    "set": fields.Set(
                        fields.Nested(
                            schemas.Schema.from_dict(
                                {"index": fields.Int(), "value": fields.String()}
                            )
                        )
                    )
                }
            )(),
            ["set", "50", "index"],
            [fields.Set, schemas.Schema, fields.Int],
            id="set_deep",
        ),
    ],
)
def test_get_by_path(
    subject: schemas.Schema,
    path: typing.Sequence[str],
    want: typing.Optional[typing.Sequence[str]],
):
    result = subject.get_by_path(path)

    if want is None:
        assert result is None
    else:
        assert result is not None

        for expected_class, actual_instance in itertools.zip_longest(want, result):
            assert isinstance(actual_instance, expected_class)


@pytest.mark.parametrize(
    "subject,want",
    [
        pytest.param(
            schemas.Block(
                attributes={
                    "computed": schemas.Attribute(type=["list", "bool"], computed=True),
                    "optional": schemas.Attribute(type="string", optional=True),
                    "optional_computed": schemas.Attribute(
                        type=["map", "bool"], optional=True, computed=True,
                    ),
                    "required": schemas.Attribute(type="number", required=True),
                }
            ),
            tfplugin5_1_pb2.Schema.Block(
                attributes=[
                    tfplugin5_1_pb2.Schema.Attribute(
                        name="computed", type=b'["list","bool"]', computed=True,
                    ),
                    tfplugin5_1_pb2.Schema.Attribute(
                        name="optional", type=b'"string"', optional=True,
                    ),
                    tfplugin5_1_pb2.Schema.Attribute(
                        name="optional_computed",
                        type=b'["map","bool"]',
                        optional=True,
                        computed=True,
                    ),
                    tfplugin5_1_pb2.Schema.Attribute(
                        name="required", type=b'"number"', required=True,
                    ),
                ]
            ),
            id="attributes",
        ),
        pytest.param(
            schemas.Block(
                block_types={
                    "list": schemas.NestedBlock(nesting=schemas.NestingMode.LIST),
                    "map": schemas.NestedBlock(nesting=schemas.NestingMode.MAP),
                    "set": schemas.NestedBlock(nesting=schemas.NestingMode.SET),
                    "single": schemas.NestedBlock(
                        nesting=schemas.NestingMode.SINGLE,
                        block=schemas.Block(
                            attributes={
                                "foo": schemas.Attribute(type="dynamic", required=True)
                            }
                        ),
                    ),
                }
            ),
            tfplugin5_1_pb2.Schema.Block(
                block_types=[
                    tfplugin5_1_pb2.Schema.NestedBlock(
                        type_name="list",
                        nesting=tfplugin5_1_pb2.Schema.NestedBlock.LIST,
                        block=tfplugin5_1_pb2.Schema.Block(),
                    ),
                    tfplugin5_1_pb2.Schema.NestedBlock(
                        type_name="map",
                        nesting=tfplugin5_1_pb2.Schema.NestedBlock.MAP,
                        block=tfplugin5_1_pb2.Schema.Block(),
                    ),
                    tfplugin5_1_pb2.Schema.NestedBlock(
                        type_name="set",
                        nesting=tfplugin5_1_pb2.Schema.NestedBlock.SET,
                        block=tfplugin5_1_pb2.Schema.Block(),
                    ),
                    tfplugin5_1_pb2.Schema.NestedBlock(
                        type_name="single",
                        nesting=tfplugin5_1_pb2.Schema.NestedBlock.SINGLE,
                        block=tfplugin5_1_pb2.Schema.Block(
                            attributes=[
                                tfplugin5_1_pb2.Schema.Attribute(
                                    name="foo", type=b'"dynamic"', required=True,
                                )
                            ]
                        ),
                    ),
                ]
            ),
            id="blocks",
        ),
        pytest.param(
            schemas.Block(
                block_types={
                    "single": schemas.NestedBlock(
                        nesting=schemas.NestingMode.SINGLE,
                        block=schemas.Block(
                            block_types={
                                "list": schemas.NestedBlock(
                                    nesting=schemas.NestingMode.LIST,
                                    block=schemas.Block(
                                        block_types={
                                            "set": schemas.NestedBlock(
                                                nesting=schemas.NestingMode.SET,
                                            )
                                        }
                                    ),
                                )
                            }
                        ),
                    ),
                }
            ),
            tfplugin5_1_pb2.Schema.Block(
                block_types=[
                    tfplugin5_1_pb2.Schema.NestedBlock(
                        type_name="single",
                        nesting=tfplugin5_1_pb2.Schema.NestedBlock.SINGLE,
                        block=tfplugin5_1_pb2.Schema.Block(
                            block_types=[
                                tfplugin5_1_pb2.Schema.NestedBlock(
                                    type_name="list",
                                    nesting=tfplugin5_1_pb2.Schema.NestedBlock.LIST,
                                    block=tfplugin5_1_pb2.Schema.Block(
                                        block_types=[
                                            tfplugin5_1_pb2.Schema.NestedBlock(
                                                type_name="set",
                                                nesting=tfplugin5_1_pb2.Schema.NestedBlock.SET,  # noqa
                                                block=tfplugin5_1_pb2.Schema.Block(),
                                            )
                                        ]
                                    ),
                                )
                            ]
                        ),
                    ),
                ]
            ),
            id="deep block nesting",
        ),
    ],
)
def test_block_to_proto(subject: schemas.Block, want: tfplugin5_1_pb2.Schema.Block):
    assert subject.to_proto() == want
