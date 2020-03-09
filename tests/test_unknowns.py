import typing

import pytest

from terraform import schemas, unknowns


@pytest.mark.parametrize(
    "schema,value,expected_value",
    [
        pytest.param(schemas.Block(), None, None, id="empty",),
        pytest.param(
            schemas.Block(
                attributes={
                    "foo": schemas.Attribute(type="string", optional=True),
                    "bar": schemas.Attribute(type="string", computed=True),
                },
                block_types={
                    "baz": schemas.NestedBlock(
                        nesting=schemas.NestingMode.SINGLE,
                        block=schemas.Block(
                            attributes={
                                "boz": schemas.Attribute(
                                    type="string", optional=True, computed=True
                                ),
                                "biz": schemas.Attribute(
                                    type="string", optional=True, computed=True
                                ),
                            }
                        ),
                    )
                },
            ),
            None,
            {"foo": None, "bar": unknowns.UNKNOWN},
            id="no prior",
        ),
        pytest.param(
            schemas.Block(
                attributes={"foo": schemas.Attribute(type="string")},
                block_types={
                    "baz": schemas.NestedBlock(
                        nesting=schemas.NestingMode.SET,
                        block=schemas.Block(
                            attributes={
                                "boz": schemas.Attribute(
                                    type="string", optional=True, computed=True
                                ),
                            }
                        ),
                    )
                },
            ),
            None,
            None,
            id="null stays null",
        ),
        pytest.param(
            schemas.Block(
                attributes={"foo": schemas.Attribute(type="string", computed=True)},
                block_types={
                    "baz": schemas.NestedBlock(
                        nesting=schemas.NestingMode.SET,
                        block=schemas.Block(
                            attributes={
                                "boz": schemas.Attribute(
                                    type="string", optional=True, computed=True
                                ),
                            }
                        ),
                    )
                },
            ),
            None,
            {"foo": unknowns.UNKNOWN},
            id="no prior with set",
        ),
        pytest.param(
            schemas.Block(
                attributes={
                    "foo": schemas.Attribute(type="string", optional=True),
                    "bar": schemas.Attribute(type="string", computed=True),
                    "baz": schemas.Attribute(
                        type="string", optional=True, computed=True
                    ),
                    "boz": schemas.Attribute(
                        type="string", optional=True, computed=True
                    ),
                },
            ),
            {"foo": "bonjour", "bar": "petit dejeuner", "baz": "grande dejeuner"},
            {
                "foo": "bonjour",
                "bar": "petit dejeuner",
                "baz": "grande dejeuner",
                "boz": unknowns.UNKNOWN,
            },
            id="prior attributes",
        ),
        pytest.param(
            schemas.Block(
                block_types={
                    "foo": schemas.NestedBlock(
                        nesting=schemas.NestingMode.SINGLE,
                        block=schemas.Block(
                            attributes={
                                "bar": schemas.Attribute(
                                    type="string", optional=True, computed=True
                                ),
                                "baz": schemas.Attribute(
                                    type="string", optional=True, computed=True
                                ),
                            }
                        ),
                    )
                }
            ),
            {"foo": {"bar": "beep"}},
            {"foo": {"bar": "beep", "baz": unknowns.UNKNOWN}},
            id="prior nested single",
        ),
        pytest.param(
            schemas.Block(
                block_types={
                    "foo": schemas.NestedBlock(
                        nesting=schemas.NestingMode.LIST,
                        block=schemas.Block(
                            attributes={
                                "bar": schemas.Attribute(
                                    type="string", optional=True, computed=True
                                ),
                                "baz": schemas.Attribute(
                                    type="string", optional=True, computed=True
                                ),
                            }
                        ),
                    )
                }
            ),
            {"foo": [{"bar": "bap"}, {"bar": "blep"}]},
            {
                "foo": [
                    {"bar": "bap", "baz": unknowns.UNKNOWN},
                    {"bar": "blep", "baz": unknowns.UNKNOWN},
                ]
            },
            id="prior nested list",
        ),
        pytest.param(
            schemas.Block(
                block_types={
                    "foo": schemas.NestedBlock(
                        nesting=schemas.NestingMode.MAP,
                        block=schemas.Block(
                            attributes={
                                "bar": schemas.Attribute(
                                    type="string", optional=True, computed=True
                                ),
                                "baz": schemas.Attribute(
                                    type="string", optional=True, computed=True
                                ),
                            }
                        ),
                    )
                }
            ),
            {
                "foo": {
                    "a": {"bar": None, "baz": "boop"},
                    "b": {"bar": "blep", "baz": None},
                }
            },
            {
                "foo": {
                    "a": {"bar": unknowns.UNKNOWN, "baz": "boop"},
                    "b": {"bar": "blep", "baz": unknowns.UNKNOWN},
                }
            },
            id="prior nested map",
        ),
        pytest.param(
            schemas.Block(
                block_types={
                    "foo": schemas.NestedBlock(
                        nesting=schemas.NestingMode.SET,
                        block=schemas.Block(
                            attributes={
                                "bar": schemas.Attribute(type="string", optional=True),
                                "baz": schemas.Attribute(
                                    type="string", optional=True, computed=True
                                ),
                            }
                        ),
                    )
                }
            ),
            {"foo": [{"bar": "blep", "baz": None}, {"bar": "boop", "baz": None}]},
            {
                "foo": [
                    {"bar": "blep", "baz": unknowns.UNKNOWN},
                    {"bar": "boop", "baz": unknowns.UNKNOWN},
                ]
            },
            id="prior nested set",
        ),
        pytest.param(
            schemas.Block(
                block_types={
                    "foo": schemas.NestedBlock(
                        nesting=schemas.NestingMode.SET,
                        block=schemas.Block(
                            attributes={
                                "bar": schemas.Attribute(type="string", optional=True),
                                "baz": schemas.Attribute(
                                    type="string", optional=True, computed=True
                                ),
                            }
                        ),
                    )
                }
            ),
            {
                "foo": [
                    {"bar": "boop", "baz": None},
                    {"bar": "boop", "baz": unknowns.UNKNOWN},
                ]
            },
            {
                "foo": [
                    {"bar": "boop", "baz": unknowns.UNKNOWN},
                    {"bar": "boop", "baz": unknowns.UNKNOWN},
                ]
            },
            id="sets differing only by unknown",
        ),
    ],
)
def test_set_unknowns(
    schema: schemas.Block,
    value: typing.Dict[str, typing.Any],
    expected_value: typing.Dict[str, typing.Any],
):
    assert unknowns.set_unknowns(value=value, schema=schema) == expected_value
