import typing

import pytest

from terraform import diagnostics, fields, schemas


@pytest.mark.parametrize(
    "schema,data,expected_diagnostics",
    [
        (
            schemas.Schema.from_dict(
                {
                    "int": fields.Int(required=True),
                    "float": fields.Float(required=True),
                    "bool": fields.Bool(required=True),
                    "string": fields.String(required=True),
                },
            )(),
            {},
            diagnostics.Diagnostics(
                diagnostics=[
                    diagnostics.Diagnostic(
                        severity=diagnostics.Severity.ERROR,
                        summary="Missing data for required field.",
                        attribute_paths=[
                            diagnostics.AttributePathStepAttribute("int"),
                        ],
                    ),
                    diagnostics.Diagnostic(
                        severity=diagnostics.Severity.ERROR,
                        summary="Missing data for required field.",
                        attribute_paths=[
                            diagnostics.AttributePathStepAttribute("float"),
                        ],
                    ),
                    diagnostics.Diagnostic(
                        severity=diagnostics.Severity.ERROR,
                        summary="Missing data for required field.",
                        attribute_paths=[
                            diagnostics.AttributePathStepAttribute("bool"),
                        ],
                    ),
                    diagnostics.Diagnostic(
                        severity=diagnostics.Severity.ERROR,
                        summary="Missing data for required field.",
                        attribute_paths=[
                            diagnostics.AttributePathStepAttribute("string"),
                        ],
                    ),
                ]
            ),
        ),
        (
            schemas.Schema.from_dict(
                {
                    "list": fields.List(fields.Int(), required=True),
                    "set": fields.Set(fields.String(), optional=True),
                    "map": fields.Map(fields.Bool(), optional=True),
                    "map_default_type": fields.Map(optional=True),
                }
            )(),
            {
                "list": ["not an integer"],
                "set": [42],
                "map": {"map_key": 42, 42: "Not a string"},
                "map_default_type": {"map_key": 42},
            },
            diagnostics.Diagnostics(
                diagnostics=[
                    diagnostics.Diagnostic(
                        severity=diagnostics.Severity.ERROR,
                        summary="Not a valid integer.",
                        attribute_paths=[
                            diagnostics.AttributePathStepAttribute("list"),
                            diagnostics.AttributePathStepElement(0),
                        ],
                    ),
                    diagnostics.Diagnostic(
                        severity=diagnostics.Severity.ERROR,
                        summary="Not a valid string.",
                        attribute_paths=[
                            diagnostics.AttributePathStepAttribute("set"),
                            diagnostics.AttributePathStepElement(0),
                        ],
                    ),
                    diagnostics.Diagnostic(
                        severity=diagnostics.Severity.ERROR,
                        summary="Not a valid boolean.",
                        attribute_paths=[
                            diagnostics.AttributePathStepAttribute("map"),
                            diagnostics.AttributePathStepElement("map_key"),
                        ],
                    ),
                    diagnostics.Diagnostic(
                        severity=diagnostics.Severity.ERROR,
                        summary="Key: Not a valid string.",
                        attribute_paths=[
                            diagnostics.AttributePathStepAttribute("map"),
                            diagnostics.AttributePathStepElement(42),
                        ],
                    ),
                    diagnostics.Diagnostic(
                        severity=diagnostics.Severity.ERROR,
                        summary="Not a valid boolean.",
                        attribute_paths=[
                            diagnostics.AttributePathStepAttribute("map"),
                            diagnostics.AttributePathStepElement(42),
                        ],
                    ),
                    diagnostics.Diagnostic(
                        severity=diagnostics.Severity.ERROR,
                        summary="Not a valid string.",
                        attribute_paths=[
                            diagnostics.AttributePathStepAttribute("map_default_type"),
                            diagnostics.AttributePathStepElement("map_key"),
                        ],
                    ),
                ]
            ),
        ),
    ],
)
def test_diagnostics_from_schema_errors(
    schema: schemas.Schema,
    data: typing.Any,
    expected_diagnostics: diagnostics.Diagnostics,
):
    errors = schema.validate(data)
    actual_diagnostics = diagnostics.Diagnostics.from_schema_errors(errors=errors)
    assert actual_diagnostics == expected_diagnostics
