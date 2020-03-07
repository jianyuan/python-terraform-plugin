import pytest

from terraform import fields, schema
from terraform.protos import tfplugin5_1_pb2


class EmptySchema(schema.Schema):
    pass


class PrimitivesSchema(schema.Schema):
    int = fields.Int(name="int", required=True, description="foo bar baz")
    float = fields.Int(name="float", optional=True)
    bool = fields.Bool(name="bool", computed=True)
    string = fields.String(optional=True, computed=True)


class SimpleCollectionsSchema(schema.Schema):
    list = fields.List(fields.Int(), required=True)
    set = fields.Set(fields.String(), optional=True)
    map = fields.Map(fields.Bool(), optional=True)
    map_default_type = fields.Map(optional=True)


class IncorrectCollectionsSchema(schema.Schema):
    list = fields.List(fields.Int(), required=True)
    set = fields.Set(fields.String(), optional=True)
    map = fields.Map(fields.Bool(), optional=True)


class SubresourceCollectionsSchema(schema.Schema):
    list = fields.List(
        fields.Nested(schema.Resource()), required=True, min_items=1, max_items=2,
    )
    set = fields.Set(fields.Nested(schema.Resource()), required=True,)
    map = fields.Map(fields.Nested(schema.Resource()), optional=True,)


class SubresourceCollectionsMinItemsAndOptionalSchema(schema.Schema):
    list = fields.List(
        fields.Nested(schema.Resource()), optional=True, min_items=1, max_items=1,
    )
    set = fields.Set(
        fields.Nested(schema.Resource()), optional=True, min_items=1, max_items=1,
    )


class SubresourceCollectionsMinItemsAndComputedSchema(schema.Schema):
    list = fields.List(
        fields.Nested(schema.Resource()), computed=True, min_items=1, max_items=1,
    )
    set = fields.Set(
        fields.Nested(schema.Resource()), computed=True, min_items=1, max_items=1,
    )


class NestedAttributesAndBlocks_Resource(schema.Resource):
    bar = fields.List(
        fields.Nested(fields.List(fields.Nested(fields.String()))), required=True,
    )
    baz = fields.Set(fields.Nested(schema.Resource()), optional=True)


class NestedAttributesAndBlocksSchema(schema.Schema):
    foo = fields.List(
        fields.Nested(NestedAttributesAndBlocks_Resource()), required=True
    )


class SensitiveSchema(schema.Schema):
    string = fields.String(optional=True, sensitive=True)


# class ConditionallyRequiredOnSchema(schema.Schema):
#     string = fields.String(required=True, missing=lambda: None)


# class ConditionallyRequiredOffSchema(schema.Schema):
#     string = fields.String(required=True, missing=lambda: "boop")


# def conditionally_required_error_schema_missing():
#     raise ValueError
#
#
# class ConditionallyRequiredErrorSchema(schema.Schema):
#     string = fields.String(required=True, missing=conditionally_required_error_schema_missing)


@pytest.mark.parametrize(
    "subject,want",
    [
        (EmptySchema(), schema.Block()),
        (
            PrimitivesSchema(),
            schema.Block(
                attributes={
                    "int": schema.Attribute(
                        type="number", required=True, description="foo bar baz",
                    ),
                    "float": schema.Attribute(type="number", optional=True,),
                    "bool": schema.Attribute(type="bool", computed=True,),
                    "string": schema.Attribute(
                        type="string", optional=True, computed=True,
                    ),
                },
            ),
        ),
        (
            SimpleCollectionsSchema(),
            schema.Block(
                attributes={
                    "list": schema.Attribute(type=["list", "number"], required=True,),
                    "set": schema.Attribute(type=["set", "string"], optional=True,),
                    "map": schema.Attribute(type=["map", "bool"], optional=True,),
                    "map_default_type": schema.Attribute(
                        type=["map", "string"], optional=True,
                    ),
                },
            ),
        ),
        (
            IncorrectCollectionsSchema(),
            schema.Block(
                attributes={
                    "list": schema.Attribute(type=["list", "number"], required=True,),
                    "set": schema.Attribute(type=["set", "string"], optional=True,),
                    "map": schema.Attribute(type=["map", "bool"], optional=True,),
                }
            ),
        ),
        (
            SubresourceCollectionsSchema(),
            schema.Block(
                attributes={
                    "map": schema.Attribute(type=["map", "string"], optional=True,),
                },
                block_types={
                    "list": schema.NestedBlock(
                        nesting=schema.NestingMode.LIST,
                        block=schema.Block(),
                        min_items=1,
                        max_items=2,
                    ),
                    "set": schema.NestedBlock(
                        nesting=schema.NestingMode.SET,
                        block=schema.Block(),
                        min_items=1,
                    ),
                },
            ),
        ),
        (
            SubresourceCollectionsMinItemsAndOptionalSchema(),
            schema.Block(
                block_types={
                    "list": schema.NestedBlock(
                        nesting=schema.NestingMode.LIST,
                        block=schema.Block(),
                        min_items=0,
                        max_items=1,
                    ),
                    "set": schema.NestedBlock(
                        nesting=schema.NestingMode.SET,
                        block=schema.Block(),
                        min_items=0,
                        max_items=1,
                    ),
                }
            ),
        ),
        (
            SubresourceCollectionsMinItemsAndComputedSchema(),
            schema.Block(
                attributes={
                    "list": schema.Attribute(
                        type=["list", ["object", {}]], computed=True,
                    ),
                    "set": schema.Attribute(
                        type=["set", ["object", {}]], computed=True,
                    ),
                }
            ),
        ),
        (
            NestedAttributesAndBlocksSchema(),
            schema.Block(
                block_types={
                    "foo": schema.NestedBlock(
                        nesting=schema.NestingMode.LIST,
                        block=schema.Block(
                            attributes={
                                "bar": schema.Attribute(
                                    type=["list", ["list", "string"]], required=True,
                                )
                            },
                            block_types={
                                "baz": schema.NestedBlock(
                                    nesting=schema.NestingMode.SET,
                                    block=schema.Block(),
                                )
                            },
                        ),
                        min_items=1,
                    )
                }
            ),
        ),
        (
            SensitiveSchema(),
            schema.Block(
                attributes={
                    "string": schema.Attribute(
                        type="string", optional=True, sensitive=True
                    )
                }
            ),
        ),
        # (
        #     ConditionallyRequiredOnSchema(),
        #     schema.Block(
        #         attributes={
        #             "string": schema.Attribute(
        #                 type="string", required=True
        #             )
        #         }
        #     ),
        # ),
        # (
        #     ConditionallyRequiredOffSchema(),
        #     schema.Block(
        #         attributes={
        #             "string": schema.Attribute(
        #                 type="string", optional=True
        #             )
        #         }
        #     ),
        # ),
        # (
        #     ConditionallyRequiredErrorSchema(),
        #     schema.Block(
        #         attributes={
        #             "string": schema.Attribute(
        #                 type="string", optional=True
        #             )
        #         }
        #     ),
        # ),
    ],
    ids=lambda arg: arg.__class__.__name__,
)
def test_schema(subject: schema.Schema, want: schema.Block):
    assert subject.to_block() == want


@pytest.mark.parametrize(
    "subject,want",
    [
        pytest.param(
            schema.Block(
                attributes={
                    "computed": schema.Attribute(type=["list", "bool"], computed=True),
                    "optional": schema.Attribute(type="string", optional=True),
                    "optional_computed": schema.Attribute(
                        type=["map", "bool"], optional=True, computed=True,
                    ),
                    "required": schema.Attribute(type="number", required=True),
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
            schema.Block(
                block_types={
                    "list": schema.NestedBlock(nesting=schema.NestingMode.LIST),
                    "map": schema.NestedBlock(nesting=schema.NestingMode.MAP),
                    "set": schema.NestedBlock(nesting=schema.NestingMode.SET),
                    "single": schema.NestedBlock(
                        nesting=schema.NestingMode.SINGLE,
                        block=schema.Block(
                            attributes={
                                "foo": schema.Attribute(type="dynamic", required=True)
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
            schema.Block(
                block_types={
                    "single": schema.NestedBlock(
                        nesting=schema.NestingMode.SINGLE,
                        block=schema.Block(
                            block_types={
                                "list": schema.NestedBlock(
                                    nesting=schema.NestingMode.LIST,
                                    block=schema.Block(
                                        block_types={
                                            "set": schema.NestedBlock(
                                                nesting=schema.NestingMode.SET,
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
                                                nesting=tfplugin5_1_pb2.Schema.NestedBlock.SET,
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
    ids=lambda arg: arg.__class__.__name__,
)
def test_block_to_proto(subject: schema.Block, want: tfplugin5_1_pb2.Schema.Block):
    assert subject.to_proto() == want
