from fractions import Fraction
from typing import Annotated

from pydantic import PlainSerializer, PlainValidator, WithJsonSchema


def _parse_fraction(value: object) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        return Fraction(value)
    msg = f"cannot parse Fraction from {value!r}"
    raise TypeError(msg)


def _serialize_fraction(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


FractionField = Annotated[
    Fraction,
    PlainValidator(_parse_fraction),
    PlainSerializer(_serialize_fraction, return_type=str),
    WithJsonSchema({"type": "string", "pattern": r"^-?\d+/\d+$", "examples": ["1/12"]}),
]
