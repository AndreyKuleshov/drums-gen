from fractions import Fraction
from itertools import pairwise

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from drumgen.domain.enums import AccentMode, Difficulty
from drumgen.domain.models import Stroke, TimeSignature
from drumgen.generator import (
    GenerateRequest,
    GenerationError,
    _is_metric_strong,  # pyright: ignore[reportPrivateUsage]
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


def test_generate_rejects_oversized_cell_count():
    # 64 bars * (12/8)/(1/24) = 64 * 36 = 2304 cells > 1024 limit,
    # while num_bars itself stays within the <=64 Field bound.
    with pytest.raises(GenerationError):
        generate(
            _req(
                time_sig=TimeSignature(num=12, den=8),
                num_bars=64,
                min_subdivision=Fraction(1, 24),
            )
        )


def test_metric_strong_simple_meter():
    beat = Fraction(1, 4)  # quarter-note beat in 4/4
    assert _is_metric_strong(Fraction(0), beat) is True
    assert _is_metric_strong(Fraction(1, 4), beat) is True
    assert _is_metric_strong(Fraction(1, 8), beat) is False


def test_metric_strong_compound_meter():
    beat = Fraction(3, 8)  # dotted-quarter beat in 6/8
    assert _is_metric_strong(Fraction(0), beat) is True
    assert _is_metric_strong(Fraction(3, 8), beat) is True
    assert _is_metric_strong(Fraction(1, 8), beat) is False


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


def test_strokes_are_tagged_with_contiguous_rudiment_groups():
    phrase = generate(_req(num_bars=2))
    groups = [s.group for b in phrase.bars for s in b.strokes]
    # groups form contiguous blocks starting at 0, incrementing by 1
    assert groups[0] == 0
    for prev, cur in pairwise(groups):
        assert cur in (prev, prev + 1)
    # every stroke in a group shares the same group value (trivially true) and
    # each distinct group has at least one stroke
    assert max(groups) + 1 == len(set(groups))


def test_mixed_mode_varies_note_durations():
    # Uniform mode: all durations equal the subdivision.
    uniform = generate(_req(num_bars=2))
    durs_uniform = {s.duration for b in uniform.bars for s in b.strokes}
    assert durs_uniform == {Fraction(1, 16)}

    # Mixed mode can mix note values: across seeds at least one phrase uses more
    # than one distinct duration, and every phrase stays valid and exactly filled.
    saw_mixed = False
    for seed in range(12):
        mixed = generate(_req(num_bars=2, mixed=True, seed=seed))
        strokes = [s for b in mixed.bars for s in b.strokes]
        assert find_violations(strokes) == []
        for bar in mixed.bars:
            total = sum((s.duration for s in bar.strokes), Fraction(0))
            assert total == bar.time_sig.bar_length
        if len({s.duration for s in strokes}) > 1:
            saw_mixed = True
    assert saw_mixed


@settings(max_examples=20, deadline=None)
@given(
    num=st.sampled_from([2, 3, 4]),
    num_bars=st.integers(min_value=1, max_value=3),
    mode=st.sampled_from(list(AccentMode)),
    seed=st.integers(min_value=0, max_value=1000),
)
def test_property_mixed_always_valid(num: int, num_bars: int, mode: AccentMode, seed: int):
    phrase = generate(
        _req(
            time_sig=TimeSignature(num=num, den=4),
            num_bars=num_bars,
            min_subdivision=Fraction(1, 16),
            accent_mode=mode,
            mixed=True,
            seed=seed,
        )
    )
    strokes = [s for b in phrase.bars for s in b.strokes]
    assert find_violations(strokes) == []
    for bar in phrase.bars:
        total = sum((s.duration for s in bar.strokes), Fraction(0))
        assert total == bar.time_sig.bar_length


def test_authentic_rolls_have_longer_release():
    from drumgen.catalog import MVP_CATALOG

    five = next(t for t in MVP_CATALOG if t.id == "five-stroke-roll")
    assert five.total_weight == 6  # 1+1+1+1+2
    assert five.elements[-1].weight == 2

    # In authentic mode, whenever a roll is placed its release note is longer
    # than the base value; across seeds at least one phrase shows the mix.
    saw_long = False
    for seed in range(12):
        p = generate(_req(num_bars=2, authentic=True, seed=seed))
        strokes = [s for b in p.bars for s in b.strokes]
        assert find_violations(strokes) == []
        for bar in p.bars:
            total = sum((s.duration for s in bar.strokes), Fraction(0))
            assert total == bar.time_sig.bar_length
        if any(s.duration == Fraction(1, 8) for s in strokes):  # 2 * 1/16
            saw_long = True
    assert saw_long


def test_authentic_off_keeps_uniform_durations():
    # Weights are ignored unless authentic is on.
    p = generate(_req(num_bars=2))
    assert {s.duration for b in p.bars for s in b.strokes} == {Fraction(1, 16)}


def _loop_safe(strokes: list[Stroke]) -> bool:
    # Rules must hold across the wrap-around seam (last strokes -> first strokes).
    return not find_violations(strokes[-2:] + strokes[:2])


def test_generated_phrases_are_loop_safe():
    for seed in range(30):
        for num in (2, 3, 4):
            for feel in ({}, {"mixed": True}, {"authentic": True}):
                p = generate(
                    _req(time_sig=TimeSignature(num=num, den=4), num_bars=2, seed=seed, **feel)
                )
                strokes = [s for b in p.bars for s in b.strokes]
                assert find_violations(strokes) == []
                assert _loop_safe(strokes), (seed, num, feel)


def test_beginner_never_uses_grace_notes():
    # Flams/drags are pro-only; beginner stays valid and ornament-free.
    for seed in range(15):
        p = generate(_req(difficulty=Difficulty.BEGINNER, num_bars=2, seed=seed))
        strokes = [s for b in p.bars for s in b.strokes]
        assert find_violations(strokes) == []
        assert all(s.grace == 0 for s in strokes)


def test_pro_uses_flams_and_drags():
    from drumgen.catalog import MVP_CATALOG

    ids = {t.id for t in MVP_CATALOG}
    assert {"flam-accent", "flam-tap", "drag-tap"} <= ids

    saw_flam = saw_drag = False
    for seed in range(24):
        p = generate(_req(difficulty=Difficulty.PRO, num_bars=2, seed=seed))
        strokes = [s for b in p.bars for s in b.strokes]
        assert find_violations(strokes) == []
        if any(s.grace == 1 for s in strokes):
            saw_flam = True
        if any(s.grace == 2 for s in strokes):
            saw_drag = True
    assert saw_flam
    assert saw_drag
