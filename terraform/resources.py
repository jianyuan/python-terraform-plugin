import dataclasses
import typing

from terraform import fields, schemas


@dataclasses.dataclass
class ResourceConfig(typing.MutableMapping):
    schema: schemas.Schema
    config: typing.Dict[str, typing.Any] = dataclasses.field(default_factory=dict)

    def __getitem__(self, key: str) -> typing.Any:
        parts = key.split(".")
        if len(parts) == 1 and parts[0] == "":
            parts = None

        current = self.config

        for i, part in enumerate(parts):
            if current is None:
                raise KeyError

            if isinstance(current, typing.Dict):
                try:
                    current = current[part]
                except KeyError:
                    if i > 0 and i != len(parts) - 1:
                        try_key = ".".join(parts[i:])
                        return current[try_key]
                    raise

            elif isinstance(current, typing.List):
                if part == "#":
                    if any(v == fields.missing for v in current):
                        return fields.missing
                    current = len(current)
                else:
                    part = int(part)
                    if part < 0 or part >= len(current):
                        raise KeyError
                    current = current[part]

            elif isinstance(current, str):
                raise NotImplementedError

            else:
                raise NotImplementedError

        return current

    def __setitem__(self, key: str, value: typing.Any) -> None:
        raise NotImplementedError

    def __delitem__(self, key: str) -> None:
        raise NotImplementedError

    def __len__(self) -> int:
        return len(self.config)

    def __iter__(self):
        return iter(self.config)

    def is_computed(self, key: str) -> bool:
        return has_missing(self.get(key))


def has_missing(obj: typing.Any) -> bool:
    stack = [obj]
    while stack:
        item = stack.pop()
        if item == fields.missing:
            return True
        elif isinstance(item, typing.Dict):
            stack.extend(item.values())
        elif isinstance(item, typing.List):
            stack.extend(item)
    return False
