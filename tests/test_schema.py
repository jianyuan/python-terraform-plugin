import pytest

from terraform import fields, schema


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
                        type=schema.encode_type("number"),
                        required=True,
                        description="foo bar baz",
                    ),
                    "float": schema.Attribute(
                        type=schema.encode_type("number"), optional=True,
                    ),
                    "bool": schema.Attribute(
                        type=schema.encode_type("bool"), computed=True,
                    ),
                    "string": schema.Attribute(
                        type=schema.encode_type("string"), optional=True, computed=True,
                    ),
                },
            ),
        ),
        (
            SimpleCollectionsSchema(),
            schema.Block(
                attributes={
                    "list": schema.Attribute(
                        type=schema.encode_type(["list", "number"]), required=True,
                    ),
                    "set": schema.Attribute(
                        type=schema.encode_type(["set", "string"]), optional=True,
                    ),
                    "map": schema.Attribute(
                        type=schema.encode_type(["map", "bool"]), optional=True,
                    ),
                    "map_default_type": schema.Attribute(
                        type=schema.encode_type(["map", "string"]), optional=True,
                    ),
                },
            ),
        ),
        (
            IncorrectCollectionsSchema(),
            schema.Block(
                attributes={
                    "list": schema.Attribute(
                        type=schema.encode_type(["list", "number"]), required=True,
                    ),
                    "set": schema.Attribute(
                        type=schema.encode_type(["set", "string"]), optional=True,
                    ),
                    "map": schema.Attribute(
                        type=schema.encode_type(["map", "bool"]), optional=True,
                    ),
                }
            ),
        ),
        (
            SubresourceCollectionsSchema(),
            schema.Block(
                attributes={
                    "map": schema.Attribute(
                        type=schema.encode_type(["map", "string"]), optional=True,
                    ),
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
                        type=schema.encode_type(["list", ["object", {}]]),
                        computed=True,
                    ),
                    "set": schema.Attribute(
                        type=schema.encode_type(["set", ["object", {}]]), computed=True,
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
                                    type=schema.encode_type(
                                        ["list", ["list", "string"]]
                                    ),
                                    required=True,
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
                        type=schema.encode_type("string"), optional=True, sensitive=True
                    )
                }
            ),
        ),
        # (
        #     ConditionallyRequiredOnSchema(),
        #     schema.Block(
        #         attributes={
        #             "string": schema.Attribute(
        #                 type=schema.encode_type("string"), required=True
        #             )
        #         }
        #     ),
        # ),
        # (
        #     ConditionallyRequiredOffSchema(),
        #     schema.Block(
        #         attributes={
        #             "string": schema.Attribute(
        #                 type=schema.encode_type("string"), optional=True
        #             )
        #         }
        #     ),
        # ),
        # (
        #     ConditionallyRequiredErrorSchema(),
        #     schema.Block(
        #         attributes={
        #             "string": schema.Attribute(
        #                 type=schema.encode_type("string"), optional=True
        #             )
        #         }
        #     ),
        # ),
    ],
    ids=lambda arg: arg.__class__.__name__,
)
def test_schema(subject: schema.Schema, want: schema.Block):
    assert subject.to_block() == want
