from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from drumgen.domain.enums import AccentMode
from drumgen.domain.models import TimeSignature
from drumgen.generator import (
    GenerateRequest,
    GenerationError,
    _metric_strong_cells,  # pyright: ignore[reportPrivateUsage]
    generate,
)
from drumgen.rules import find_violations


def _req(**kw: object) -> GenerateRequest:
    base: dict[str, object] = {
        "time_sig": TimeSignature(num=4, den=4),
        "num_bars": 1,
        "min_subdivision": Fraction(1, 16),
        "tempo_bpm": 100,
        "accent_mode": AccentMode.RUDIMENT,
        "seed": 1,
    }
    base.update(kw)
    return GenerateRequest.model_validate(base)


def test_generate_fills_bar_exactly():
    phrase = generate(_req())
    total = sum((s.duration for b in phrase.bars for s in b.strokes), Fraction(0))
    assert total == Fraction(4, 4)
    assert all(s.duration == Fraction(1, 16) for b in phrase.bars for s in b.strokes)


def test_generate_output_has_no_rule_violations():
    strokes = [s for b in generate(_req()).bars for s in b.strokes]
    assert find_violations(strokes) == []


def test_generate_multi_bar():
    phrase = generate(_req(num_bars=4))
    assert len(phrase.bars) == 4


def test_generate_rejects_non_integer_grid():
    # 3/8 bar with triplet-16th 1/24 grid -> (3/8)/(1/24) = 9 -> ok; use a mismatch instead
    with pytest.raises(GenerationError):
        generate(_req(time_sig=TimeSignature(num=3, den=8), min_subdivision=Fraction(1, 5)))


def test_generate_rejects_nonpositive_subdivision():
    with pytest.raises(GenerationError):
        generate(_req(min_subdivision=Fraction(0)))


def test_metric_strong_cells_simple_meter():
    assert _metric_strong_cells(TimeSignature(num=4, den=4), Fraction(1, 8)) == {0, 2, 4, 6}


def test_metric_strong_cells_compound_meter():
    assert _metric_strong_cells(TimeSignature(num=6, den=8), Fraction(1, 8)) == {0, 3}


def test_seed_is_reproducible():
    a = generate(_req(seed=42)).model_dump(mode="json")
    b = generate(_req(seed=42)).model_dump(mode="json")
    assert a == b


def test_metric_mode_accents_downbeats():
    phrase = generate(_req(accent_mode=AccentMode.METRIC, min_subdivision=Fraction(1, 4)))
    # 4/4 with quarter grid: 4 cells, strong cell is index 0 of the bar
    accents = [s.accent for s in phrase.bars[0].strokes]
    assert accents[0] is True


@settings(max_examples=25, deadline=None)
@given(
    num=st.sampled_from([2, 3, 4]),
    num_bars=st.integers(min_value=1, max_value=3),
    mode=st.sampled_from(list(AccentMode)),
    seed=st.integers(min_value=0, max_value=1000),
)
def test_property_always_valid(num: int, num_bars: int, mode: AccentMode, seed: int):
    phrase = generate(
        _req(
            time_sig=TimeSignature(num=num, den=4),
            num_bars=num_bars,
            min_subdivision=Fraction(1, 16),
            accent_mode=mode,
            seed=seed,
        )
    )
    strokes = [s for b in phrase.bars for s in b.strokes]
    assert find_violations(strokes) == []
    for bar in phrase.bars:
        total = sum((s.duration for s in bar.strokes), Fraction(0))
        assert total == bar.time_sig.bar_length
