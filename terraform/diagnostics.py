import abc
import dataclasses
import enum
import functools
import typing

from terraform.protos import tfplugin5_1_pb2


class Severity(enum.Enum):
    INVALID = enum.auto()
    ERROR = enum.auto()
    WARNING = enum.auto()

    def to_proto(self) -> tfplugin5_1_pb2.Diagnostic.Severity:
        return SEVERITY_PROTO_ENUMS[self]


SEVERITY_PROTO_ENUMS = {
    Severity.INVALID: tfplugin5_1_pb2.Diagnostic.Severity.INVALID,
    Severity.ERROR: tfplugin5_1_pb2.Diagnostic.Severity.ERROR,
    Severity.WARNING: tfplugin5_1_pb2.Diagnostic.Severity.WARNING,
}


@functools.total_ordering
class BaseAttributePathStep(abc.ABC):
    @abc.abstractmethod
    def to_proto(self) -> typing.Union[tfplugin5_1_pb2.AttributePath.Step]:
        ...

    def __lt__(self, other):
        return str(self) < str(other)


@dataclasses.dataclass
class AttributePathStepAttribute(BaseAttributePathStep):
    attribute_name: str

    def __str__(self):
        return self.attribute_name

    def to_proto(self) -> typing.Union[tfplugin5_1_pb2.AttributePath.Step]:
        return tfplugin5_1_pb2.AttributePath.Step(attribute_name=self.attribute_name)


@dataclasses.dataclass
class AttributePathStepElement(BaseAttributePathStep):
    element_key: typing.Union[str, int]

    def __str__(self):
        return str(self.element_key)

    def to_proto(self) -> typing.Union[tfplugin5_1_pb2.AttributePath.Step]:
        if isinstance(self.element_key, str):
            return tfplugin5_1_pb2.AttributePath.Step(
                element_key_string=self.element_key
            )
        elif isinstance(self.element_key, int):
            return tfplugin5_1_pb2.AttributePath.Step(element_key_int=self.element_key)
        else:
            raise NotImplementedError


@dataclasses.dataclass(order=True)
class Diagnostic:
    severity: Severity
    summary: str
    detail: typing.Optional[str] = dataclasses.field(default=None)
    attribute_paths: typing.List[BaseAttributePathStep] = dataclasses.field(
        default_factory=list
    )

    def to_proto(self) -> tfplugin5_1_pb2.Diagnostic:
        return tfplugin5_1_pb2.Diagnostic(
            severity=self.severity.to_proto(),
            summary=self.summary,
            detail=self.detail,
            attribute=tfplugin5_1_pb2.AttributePath(
                steps=[
                    attribute_path.to_proto() for attribute_path in self.attribute_paths
                ]
            ),
        )


@dataclasses.dataclass
class Diagnostics:
    diagnostics: typing.List[Diagnostic] = dataclasses.field(default_factory=list)

    def __post_init__(self):
        self.sort()

    def sort(self):
        self.diagnostics.sort()

    def to_proto(self) -> typing.List[tfplugin5_1_pb2.Diagnostic]:
        return [diagnostic.to_proto() for diagnostic in self.diagnostics]

    @classmethod
    def from_schema_errors(
        cls,
        *,
        errors: typing.Optional[typing.Dict[str, typing.Any]],
        severity=Severity.ERROR,
    ):
        def walk_errors(
            errors: typing.List[str], steps: typing.List[BaseAttributePathStep]
        ):
            for error in errors:
                yield Diagnostic(
                    severity=severity, summary=error, attribute_paths=steps
                )

        def walk(
            errors: typing.Optional[typing.Dict[str, typing.Any]],
            steps: typing.List[BaseAttributePathStep],
        ):
            if errors is None:
                return

            for key, field_errors in errors.items():
                if isinstance(field_errors, typing.List):
                    this_steps = steps + [AttributePathStepAttribute(key)]
                    yield from walk_errors(field_errors, this_steps)
                elif isinstance(field_errors, typing.Dict):
                    for index, field_sub_errors in field_errors.items():
                        this_steps = steps + [
                            AttributePathStepAttribute(key),
                            AttributePathStepElement(index),
                        ]
                        if isinstance(field_sub_errors, typing.List):
                            yield from walk_errors(field_sub_errors, this_steps)
                        elif isinstance(field_sub_errors, typing.Dict):
                            if "key" in field_sub_errors:
                                yield from walk_errors(
                                    [
                                        f"Key: {error}"
                                        for error in field_sub_errors["key"]
                                    ],
                                    this_steps,
                                )
                            if "value" in field_sub_errors:
                                yield from walk_errors(
                                    field_sub_errors["value"], this_steps
                                )
                        else:
                            raise NotImplementedError
                else:
                    raise NotImplementedError

        return cls(diagnostics=list(walk(errors, [])))
