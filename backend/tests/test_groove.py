"""Tests for the full-kit groove generator (Pattern mode)."""

from fractions import Fraction

import pytest

from drumgen.domain.enums import Difficulty, Hand, Surface
from drumgen.domain.groove import GrooveBar, Hit
from drumgen.domain.models import TimeSignature
from drumgen.groove_generator import GrooveRequest, generate_groove

_METERS = [(4, 4), (3, 4), (6, 8), (7, 8), (5, 4)]
_DIFFS = [Difficulty.BEGINNER, Difficulty.MID, Difficulty.PRO]


def _req(
    num: int = 4, den: int = 4, difficulty: Difficulty = Difficulty.BEGINNER, seed: int = 1
) -> GrooveRequest:
    return GrooveRequest(
        time_sig=TimeSignature(num=num, den=den),
        num_bars=2,
        tempo_bpm=100,
        difficulty=difficulty,
        seed=seed,
    )


@pytest.mark.parametrize("meter", _METERS)
@pytest.mark.parametrize("difficulty", _DIFFS)
def test_generates_valid_groove(meter: tuple[int, int], difficulty: Difficulty) -> None:
    num, den = meter
    groove = generate_groove(_req(num, den, difficulty))
    bar_len = Fraction(num, den)
    assert len(groove.bars) == 2
    for bar in groove.bars:
        assert bar.hands, "hands voice should never be empty (hi-hat runs throughout)"
        assert bar.feet, "kick should always be present"
        for hit in [*bar.hands, *bar.feet]:
            assert 0 <= hit.onset < bar_len


def test_beginner_is_kick_1_and_3_hats_eighths_snare_backbeats():
    groove = generate_groove(_req(4, 4, Difficulty.BEGINNER))
    bar = groove.bars[0]
    # Kick on beats 1 and 3 (onsets 0 and 1/2 in whole-note units).
    kick_onsets = sorted(h.onset for h in bar.feet if h.surface is Surface.KICK)
    assert kick_onsets == [Fraction(0), Fraction(1, 2)]
    # Hi-hat straight eighths: 8 hits at 1/8 spacing.
    hats = sorted(h.onset for h in bar.hands if h.surface is Surface.HIHAT)
    assert hats == [Fraction(i, 8) for i in range(8)]
    # Snare on 2 & 4 (onsets 1/4 and 3/4), left hand.
    snares = sorted(h.onset for h in bar.hands if h.surface is Surface.SNARE and not h.ghost)
    assert snares == [Fraction(1, 4), Fraction(3, 4)]
    assert all(h.hand is Hand.L for h in bar.hands if h.surface is Surface.SNARE)
    assert all(h.hand is Hand.R for h in bar.hands if h.surface is Surface.HIHAT)


def test_hand_exclusivity_enforced_by_model():
    # Same hand on hi-hat AND snare at the same onset must be rejected.
    with pytest.raises(ValueError, match="double-booked"):
        GrooveBar(
            time_sig=TimeSignature(num=4, den=4),
            hands=[
                Hit(onset=Fraction(0), duration=Fraction(1, 8), surface=Surface.HIHAT, hand=Hand.R),
                Hit(onset=Fraction(0), duration=Fraction(1, 8), surface=Surface.SNARE, hand=Hand.R),
            ],
            feet=[],
        )


def test_generated_grooves_never_double_book_a_hand():
    for difficulty in _DIFFS:
        for num, den in _METERS:
            # Construction would raise if a hand were double-booked; just build many.
            for seed in range(8):
                generate_groove(_req(num, den, difficulty, seed))


def test_seed_is_deterministic():
    a = generate_groove(_req(4, 4, Difficulty.PRO, seed=42))
    b = generate_groove(_req(4, 4, Difficulty.PRO, seed=42))
    assert a.model_dump() == b.model_dump()


def test_pro_has_double_pedal_sixteenth_kicks():
    groove = generate_groove(_req(4, 4, Difficulty.PRO, seed=3))
    # At least one kick lands on a 16th subdivision (onset with denominator 16).
    assert any(h.onset.denominator == 16 for h in groove.bars[0].feet)
