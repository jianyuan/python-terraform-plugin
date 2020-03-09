import typing

import msgpack

from terraform import schemas

UNKNOWN = msgpack.ExtType(code=0, data=b"\x00")


def set_unknowns(
    value: typing.Optional[typing.Dict[str, typing.Any]], schema: schemas.Block
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    result = {}

    if value is None:
        all_none = True
        for name, attribute in schema.attributes.items():
            if attribute.computed:
                result[name] = UNKNOWN
                all_none = False
            else:
                result[name] = None
        if all_none:
            return value
        return result

    value = typing.cast(typing.Dict[str, typing.Any], value)

    for name, attribute in schema.attributes.items():
        this_value = value.get(name)
        if attribute.computed and this_value is None:
            result[name] = UNKNOWN
        else:
            result[name] = this_value

    for name, block in schema.block_types.items():
        this_value = value.get(name)
        if this_value is None:
            result[name] = UNKNOWN
        else:
            if block.nesting in {schemas.NestingMode.SINGLE, schemas.NestingMode.GROUP}:
                result[name] = set_unknowns(this_value, block.block)
            elif block.nesting in {schemas.NestingMode.LIST, schemas.NestingMode.SET}:
                result[name] = [
                    set_unknowns(inner_value, block.block) for inner_value in this_value
                ]
            elif block.nesting in {schemas.NestingMode.MAP}:
                this_result = {}
                for key, inner_value in this_value.items():
                    this_result[key] = set_unknowns(inner_value, block.block)
                result[name] = this_result
            else:
                raise NotImplementedError

    return result
