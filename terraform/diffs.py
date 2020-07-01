import dataclasses
import enum
import typing


class AttributeDiffType(enum.Enum):
    UNKNOWN = enum.auto()
    INPUT = enum.auto()
    OUTPUT = enum.auto()


@dataclasses.dataclass
class AttributeDiff:
    old: typing.Any
    new: typing.Any
    new_computed: bool = False
    new_removed: bool = False
    new_extra: typing.Any = None
    requires_new: bool = False
    sensitive: bool = False
    type: AttributeDiffType = AttributeDiffType.UNKNOWN


@dataclasses.dataclass
class InstanceDiff:
    attributes: typing.Dict[str, AttributeDiff] = dataclasses.field(
        default_factory=dict
    )
    destroy: bool = False
    destroy_deposed: bool = False
    destroy_tainted: bool = False
    meta: typing.Dict[str, typing.Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class InstanceState:
    id: typing.Optional[str] = None
    attributes: typing.Dict[str, typing.Any] = dataclasses.field(default_factory=dict)
    tainted: bool = False
