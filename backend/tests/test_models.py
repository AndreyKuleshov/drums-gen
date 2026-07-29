from fractions import Fraction

import pytest
from pydantic import ValidationError

from drumgen.domain.enums import AccentMode, Articulation, Hand, Surface
from drumgen.domain.models import Bar, Phrase, Stroke, TimeSignature


def test_enum_values():
    assert Hand.R.value == "R"
    assert Hand.L.value == "L"
    assert Articulation.NORMAL.value == "normal"
    assert Surface.SNARE.value == "snare"
    assert {m.value for m in AccentMode} == {"rudiment", "metric", "both"}


def test_bar_length_and_beat():
    assert TimeSignature(num=4, den=4).bar_length == Fraction(4, 4)
    assert TimeSignature(num=4, den=4).beat_length == Fraction(1, 4)
    assert TimeSignature(num=6, den=8).is_compound() is True
    assert TimeSignature(num=6, den=8).beat_length == Fraction(3, 8)
    assert TimeSignature(num=3, den=4).is_compound() is False


def test_bar_invariant_accepts_exact_fill():
    ts = TimeSignature(num=2, den=4)
    strokes = [Stroke(duration=Fraction(1, 4), hand=Hand.R) for _ in range(2)]
    bar = Bar(time_sig=ts, strokes=strokes)
    assert len(bar.strokes) == 2


def test_bar_invariant_rejects_wrong_sum():
    ts = TimeSignature(num=2, den=4)
    with pytest.raises(ValidationError):
        Bar(time_sig=ts, strokes=[Stroke(duration=Fraction(1, 4), hand=Hand.R)])


def test_phrase_roundtrips_json():
    ts = TimeSignature(num=1, den=4)
    phrase = Phrase(
        time_sig=ts,
        tempo_bpm=100,
        subdivision=Fraction(1, 4),
        accent_mode=AccentMode.RUDIMENT,
        bars=[Bar(time_sig=ts, strokes=[Stroke(duration=Fraction(1, 4), hand=Hand.L)])],
    )
    dumped = phrase.model_dump(mode="json")
    assert dumped["bars"][0]["strokes"][0]["duration"] == "1/4"
    assert Phrase.model_validate(dumped).tempo_bpm == 100
