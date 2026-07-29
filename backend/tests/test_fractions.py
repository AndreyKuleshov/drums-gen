from fractions import Fraction

from pydantic import BaseModel

from drumgen.domain.fractions import FractionField


class _M(BaseModel):
    d: FractionField


def test_parse_from_string():
    assert _M.model_validate({"d": "1/12"}).d == Fraction(1, 12)


def test_parse_from_fraction():
    assert _M(d=Fraction(3, 8)).d == Fraction(3, 8)


def test_parse_from_int():
    assert _M.model_validate({"d": 1}).d == Fraction(1, 1)


def test_serialize_to_string():
    assert _M(d=Fraction(1, 12)).model_dump(mode="json") == {"d": "1/12"}


def test_json_schema_is_string():
    assert _M.model_json_schema()["properties"]["d"]["type"] == "string"
