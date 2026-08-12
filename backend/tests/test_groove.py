"""Tests for the full-kit groove generator (Pattern mode)."""

from fractions import Fraction
from typing import Literal

import pytest

from drumgen.domain.enums import Difficulty, Hand, Surface
from drumgen.domain.groove import GrooveBar, Hit
from drumgen.domain.models import TimeSignature
from drumgen.groove_generator import GrooveRequest, generate_groove

_METERS = [(4, 4), (3, 4), (6, 8), (7, 8), (5, 4)]
_DIFFS = [Difficulty.BEGINNER, Difficulty.MID, Difficulty.PRO]


def _req(
    num: int = 4,
    den: int = 4,
    difficulty: Difficulty = Difficulty.BEGINNER,
    seed: int = 1,
    style: Literal["groove", "fill"] = "groove",
    hands: Literal["straight", "rudiment"] = "straight",
    num_bars: int = 2,
) -> GrooveRequest:
    return GrooveRequest(
        time_sig=TimeSignature(num=num, den=den),
        num_bars=num_bars,
        tempo_bpm=100,
        difficulty=difficulty,
        style=style,
        hands=hands,
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


def test_beginner_keeps_the_foundation_but_varies():
    bar = generate_groove(_req(4, 4, Difficulty.BEGINNER)).bars[0]
    kick_onsets = {h.onset for h in bar.feet if h.surface is Surface.KICK}
    # The 1 & 3 foundation is always present (extra syncopations may be added).
    assert {Fraction(0), Fraction(1, 2)} <= kick_onsets
    # Beginner hi-hat stays a straight-eighth ostinato (no 16th insertions); the
    # last eighth may be an open hi-hat.
    hats = sorted(h.onset for h in bar.hands if h.surface in (Surface.HIHAT, Surface.HIHAT_OPEN))
    assert hats == [Fraction(i, 8) for i in range(8)]
    # Backbeat snare on 2 & 4, accented, left hand.
    accented_snares = sorted(h.onset for h in bar.hands if h.surface is Surface.SNARE and h.accent)
    assert accented_snares == [Fraction(1, 4), Fraction(3, 4)]
    assert all(h.hand is Hand.L for h in bar.hands if h.surface is Surface.SNARE)
    assert all(h.hand is Hand.R for h in bar.hands if h.surface is Surface.HIHAT)


def test_beginner_varies_by_seed():
    dumps = [
        generate_groove(_req(4, 4, Difficulty.BEGINNER, seed=s)).model_dump() for s in range(8)
    ]
    assert any(d != dumps[0] for d in dumps), "beginner grooves should not all be identical"


def test_advanced_can_orchestrate_toms():
    # Across seeds, the advanced straight groove sometimes folds toms into the kit.
    surfaces: set[Surface] = set()
    for seed in range(12):
        bar = generate_groove(_req(4, 4, Difficulty.PRO, seed=seed)).bars[0]
        surfaces |= {h.surface for h in bar.hands}
    assert surfaces & {Surface.TOM_HIGH, Surface.TOM_MID, Surface.TOM_LOW}


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


def test_pro_double_pedal_bursts_move_around_the_bar():
    # The advanced double-pedal 16th burst appears across seeds and is NOT always on
    # the last beat (it's placed on a random beat, varied length).
    burst_beats: set[int] = set()
    saw_sixteenth = False
    for seed in range(30):
        for bar in generate_groove(_req(4, 4, Difficulty.PRO, seed=seed)).bars:
            sixteenths = [h.onset for h in bar.feet if h.onset.denominator == 16]
            if sixteenths:
                saw_sixteenth = True
                burst_beats.update(int(o * 4) for o in sixteenths)  # which beat (0..3)
    assert saw_sixteenth, "advanced grooves should sometimes have a 16th double-pedal burst"
    assert len(burst_beats) > 1, "bursts should not always land on the same beat"


def test_hands_rudiment_orchestrates_hat_and_snare():
    groove = generate_groove(_req(4, 4, Difficulty.MID, hands="rudiment", seed=5))
    surfaces = {h.surface for bar in groove.bars for h in bar.hands}
    assert Surface.SNARE in surfaces
    assert Surface.HIHAT in surfaces
    # There is at least one accented snare (the rudiment's accents land on snare).
    assert any(h.surface is Surface.SNARE and h.accent for bar in groove.bars for h in bar.hands)


def _max_same_hand_run(hits: list[Hit]) -> int:
    seq = [h.hand for h in sorted(hits, key=lambda h: h.onset)]
    best = cur = 0
    prev = None
    for hand in seq:
        cur = cur + 1 if hand == prev else 1
        prev = hand
        best = max(best, cur)
    return best


def test_rudiment_groove_is_a_groove_not_an_exercise():
    # The rudiment hands mode is now a groove: steady hi-hat + backbeat snare + ghost
    # work — beat 1 is hi-hat + kick (never a bare snare), and the hi-hat runs on the
    # right hand (an ostinato, to which the max-two rule does not apply).
    for seed in range(20):
        bar = generate_groove(_req(4, 4, Difficulty.MID, hands="rudiment", seed=seed)).bars[0]
        at_zero = [h.surface for h in bar.hands if h.onset == Fraction(0)]
        assert Surface.SNARE not in at_zero, "a groove must not start on a bare snare"
        assert Surface.HIHAT in at_zero or Surface.HIHAT_OPEN in at_zero


def test_fill_hands_never_exceed_two_same_hand():
    for seed in range(20):
        groove = generate_groove(_req(4, 4, Difficulty.PRO, style="fill", num_bars=2, seed=seed))
        for bar in groove.bars:
            assert _max_same_hand_run(bar.hands) <= 2


def test_fill_orchestrates_snare_and_toms_and_can_use_32nds():
    surfaces: set[Surface] = set()
    durations: set[Fraction] = set()
    for seed in range(12):
        groove = generate_groove(_req(4, 4, Difficulty.PRO, style="fill", num_bars=2, seed=seed))
        for bar in groove.bars:
            for h in bar.hands:
                surfaces.add(h.surface)
                durations.add(h.duration)
    # Fills move around the kit (snare + toms), not toms-only or snare-only.
    assert Surface.SNARE in surfaces
    assert surfaces & {Surface.TOM_HIGH, Surface.TOM_MID, Surface.TOM_LOW}
    # The 32nd burst appears somewhere in the advanced vocabulary.
    assert Fraction(1, 32) in durations


def test_fill_uses_toms_and_respects_bar_count():
    groove = generate_groove(_req(4, 4, Difficulty.PRO, style="fill", num_bars=4, seed=7))
    assert len(groove.bars) == 4
    surfaces = {h.surface for bar in groove.bars for h in bar.hands}
    assert surfaces & {Surface.TOM_HIGH, Surface.TOM_MID, Surface.TOM_LOW}
    # Kick grounds each bar.
    assert all(any(h.surface is Surface.KICK for h in bar.feet) for bar in groove.bars)
