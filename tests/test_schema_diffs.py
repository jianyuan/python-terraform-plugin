import typing

import pytest

from terraform import diffs, fields, schema_diffs, schemas


@pytest.mark.xfail
@pytest.mark.parametrize(
    "schema,state,config,expected_diff,expected_exception",
    [
        (
            schemas.Schema.from_dict(
                {
                    "availability_zone": fields.String(
                        optional=True, computed=True, force_new=True
                    )
                }
            ),
            None,
            {"availability_zone": "foo"},
            diffs.InstanceDiff(
                attributes={
                    "availability_zone": diffs.AttributeDiff(
                        old="", new="foo", requires_new=True
                    )
                }
            ),
            None,
        )
    ],
)
def test_schema_diff(
    schema: schemas.Schema,
    state: typing.Optional[diffs.InstanceState],
    config: typing.Dict[str, typing.Any],
    expected_diff: diffs.InstanceDiff,
    expected_exception: typing.Optional[Exception],
):
    differ = schema_diffs.SchemaDiff(schema=schema)
    assert (
        differ.diff(state=state, config=config, handle_requires_new=True)
        == expected_diff
    )
