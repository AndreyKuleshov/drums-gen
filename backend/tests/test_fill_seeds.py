"""The curated fill seed bank and its integration into the fill generator."""

import random
from fractions import Fraction

from drumgen.domain.enums import Difficulty, Hand, Surface
from drumgen.domain.groove import GrooveBar
from drumgen.domain.models import TimeSignature
from drumgen.fill_seeds import (
    FillSeed,
    is_seedable,
    seeded_fill_bars,
    seeds_by_difficulty,
)
from drumgen.groove_generator import GrooveRequest, generate_groove

_44 = TimeSignature(num=4, den=4)


def _all_seeds() -> list[FillSeed]:
    by_diff = seeds_by_difficulty()
    return [s for seeds in by_diff.values() for s in seeds]


def test_corpus_is_large_and_every_seed_is_unique():
    seeds = _all_seeds()
    assert len(seeds) >= 200, "expected the expanded 200+ corpus"

    def canonical(seed: FillSeed):
        return tuple(
            sorted(
                (h.onset, h.duration, h.surface, h.accent, h.ghost, h.articulation)
                for h in (*seed.hands, *seed.feet)
            )
        )

    keys = {canonical(s) for s in seeds}
    assert len(keys) == len(seeds), "seeds must be canonically unique — no repeats"


def test_every_difficulty_tier_has_seeds():
    by_diff = seeds_by_difficulty()
    for diff in Difficulty:
        assert by_diff[diff], f"tier {diff} has no seeds"


def test_seeds_load_as_valid_bars_in_common_time():
    # Rendering each seed builds a GrooveBar, which runs the model validators
    # (onsets within the bar, hand exclusivity). A raise here is a corpus defect.
    for diff in Difficulty:
        rng = random.Random(0)
        n = len(seeds_by_difficulty()[diff])
        bars = seeded_fill_bars(_44, diff, n, rng)
        assert bars is not None
        assert len(bars) == n


def test_sticking_never_exceeds_two_of_the_same_hand():
    for seed in _all_seeds():
        run = 1
        prev: Hand | None = None
        for h in seed.hands:
            if h.hand == prev:
                run += 1
            else:
                run = 1
            prev = h.hand
            assert run <= 2, f"{seed.id}: more than two {h.hand} strokes in a row"


def test_only_common_time_is_seedable():
    assert is_seedable(_44)
    assert not is_seedable(TimeSignature(num=6, den=8))
    assert not is_seedable(TimeSignature(num=3, den=4))


def test_non_common_meter_falls_back_to_procedural():
    rng = random.Random(1)
    assert seeded_fill_bars(TimeSignature(num=6, den=8), Difficulty.MID, 1, rng) is None
    # ...but the generator still produces a fill for that meter.
    g = generate_groove(
        GrooveRequest(
            time_sig=TimeSignature(num=6, den=8),
            num_bars=1,
            tempo_bpm=100,
            difficulty=Difficulty.MID,
            style="fill",
        )
    )
    assert len(g.bars) == 1
    assert g.bars[0].hands


def test_seeded_fill_is_deterministic():
    def build():
        return generate_groove(
            GrooveRequest(
                time_sig=_44,
                num_bars=3,
                tempo_bpm=120,
                difficulty=Difficulty.PRO,
                style="fill",
                seed=42,
            )
        ).model_dump()

    assert build() == build()


def test_multibar_fill_uses_distinct_seeds_per_bar():
    # With a pool of dozens of seeds, a short phrase should not repeat a bar.
    rng = random.Random(7)
    bars = seeded_fill_bars(_44, Difficulty.MID, 4, rng)
    assert bars is not None

    def shape(bar: GrooveBar):
        return tuple((h.onset, h.surface, h.accent, h.ghost) for h in bar.hands)

    shapes = [shape(b) for b in bars]
    assert len(set(shapes)) == len(shapes), "bars within a phrase should differ"


def test_multibar_fill_builds_toward_a_climax():
    # A multi-bar fill should develop: stroke density is non-decreasing across
    # bars, so the phrase builds into its landing rather than jumping around.
    rng = random.Random(13)
    bars = seeded_fill_bars(_44, Difficulty.PRO, 4, rng)
    assert bars is not None
    counts = [len(b.hands) for b in bars]
    assert counts == sorted(counts), f"fill should build, got {counts}"
    # The climax (last) bar is the busiest and the one that lands a kick.
    assert counts[-1] == max(counts)
    last = bars[-1]
    final_onset = max(h.onset for h in last.hands)
    assert any(f.onset == final_onset for f in last.feet)


def test_fill_is_grounded_with_a_kick_and_lands():
    g = generate_groove(
        GrooveRequest(
            time_sig=_44,
            num_bars=2,
            tempo_bpm=110,
            difficulty=Difficulty.MID,
            style="fill",
            seed=5,
        )
    )
    # Every bar has a downbeat kick foundation.
    for bar in g.bars:
        assert any(f.onset == 0 and f.surface is Surface.KICK for f in bar.feet)
    # The last bar lands a kick under its final stroke.
    last = g.bars[-1]
    final_onset = max(h.onset for h in last.hands)
    assert final_onset > 0
    assert any(f.onset == final_onset for f in last.feet)


def test_phrase_mode_puts_a_seeded_fill_every_fourth_bar():
    g = generate_groove(
        GrooveRequest(
            time_sig=_44,
            num_bars=4,
            tempo_bpm=100,
            difficulty=Difficulty.PRO,
            style="phrase",
            seed=3,
        )
    )
    assert len(g.bars) == 4
    # The 4th bar is a fill: denser hands than a plain groove bar and it resolves
    # with a landing kick under the final stroke.
    fill_bar = g.bars[3]
    final_onset = max(h.onset for h in fill_bar.hands)
    assert any(f.onset == final_onset for f in fill_bar.feet)


def test_pro_fills_can_use_thirtysecond_notes_and_toms():
    # Across the PRO tier, at least one seed uses 32nd-note density and toms.
    pro = seeds_by_difficulty()[Difficulty.PRO]
    has_32nd = any(any(h.duration == Fraction(1, 32) for h in s.hands) for s in pro)
    has_toms = any(
        any(h.surface in (Surface.TOM_HIGH, Surface.TOM_MID, Surface.TOM_LOW) for h in s.hands)
        for s in pro
    )
    assert has_32nd
    assert has_toms
