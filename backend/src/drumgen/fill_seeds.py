"""Seed bank of musical drum fills (Pattern mode).

`data/fill_seeds.json` holds a canonically-deduplicated corpus of one-bar 4/4
fills, synthesised from the standard, widely-taught families of drum fills
(8th, broken-8th, 16th linear, broken-16th, tom cascade, flam, 8th-triplet,
32nd burst, herta, ghost-16th, gospel linear, single-stroke accent). Each seed
carries onset/duration as whole-note fractions plus surface/hand/accent/ghost/
articulation, matching the `Hit` domain model.

The fill generator draws from this bank (by difficulty) so fills are recognisably
musical phrases rather than purely random note sequences, then grounds each bar
with a kick foundation and a landing kick under the final stroke.
"""

from __future__ import annotations

import json
import random
from collections.abc import Mapping
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Any

from drumgen.domain.enums import Articulation, Difficulty, Hand, Surface
from drumgen.domain.groove import GrooveBar, Hit
from drumgen.domain.models import TimeSignature

_DATA = "fill_seeds.json"
_KICK_DUR = Fraction(1, 16)


@dataclass(frozen=True)
class FillSeed:
    """One deduplicated, model-validated one-bar 4/4 fill."""

    id: str
    family: str
    difficulty: Difficulty
    hands: tuple[Hit, ...]
    feet: tuple[Hit, ...]


def _load_raw() -> Any:
    resource = files("drumgen").joinpath("data", _DATA)
    return json.loads(Path(str(resource)).read_text(encoding="utf-8"))


def _hit_from(d: Mapping[str, Any]) -> Hit:
    hand = d.get("hand")
    return Hit(
        onset=Fraction(str(d["onset"])),
        duration=Fraction(str(d["duration"])),
        surface=Surface(d["surface"]),
        hand=Hand(hand) if hand is not None else None,
        accent=bool(d["accent"]),
        ghost=bool(d["ghost"]),
        articulation=Articulation(d["articulation"]),
    )


@lru_cache(maxsize=1)
def _seeds_by_difficulty() -> dict[Difficulty, tuple[FillSeed, ...]]:
    raw = _load_raw()
    buckets: dict[Difficulty, list[FillSeed]] = {d: [] for d in Difficulty}
    for entry in raw["seeds"]:
        diff = Difficulty(entry["difficulty"])
        buckets[diff].append(
            FillSeed(
                id=str(entry["id"]),
                family=str(entry["family"]),
                difficulty=diff,
                hands=tuple(_hit_from(h) for h in entry["hands"]),
                feet=tuple(_hit_from(f) for f in entry["feet"]),
            )
        )
    return {d: tuple(seeds) for d, seeds in buckets.items()}


def seeds_by_difficulty() -> dict[Difficulty, tuple[FillSeed, ...]]:
    """The full seed bank, grouped by difficulty tier (cached)."""
    return _seeds_by_difficulty()


def is_seedable(ts: TimeSignature) -> bool:
    """Seeds are one-bar 4/4 phrases; other meters use procedural composition."""
    return ts.num == 4 and ts.den == 4


def _seeds_for(difficulty: Difficulty) -> tuple[FillSeed, ...]:
    """Seeds at this tier, widening to easier tiers if a tier is ever empty."""
    by_diff = _seeds_by_difficulty()
    order = {
        Difficulty.BEGINNER: [Difficulty.BEGINNER, Difficulty.MID, Difficulty.PRO],
        Difficulty.MID: [Difficulty.MID, Difficulty.BEGINNER, Difficulty.PRO],
        Difficulty.PRO: [Difficulty.PRO, Difficulty.MID, Difficulty.BEGINNER],
    }[difficulty]
    for d in order:
        if by_diff[d]:
            return by_diff[d]
    return ()


def _clone(hit: Hit) -> Hit:
    return Hit(
        onset=hit.onset,
        duration=hit.duration,
        surface=hit.surface,
        hand=hit.hand,
        accent=hit.accent,
        ghost=hit.ghost,
        articulation=hit.articulation,
    )


def _render(seed: FillSeed, ts: TimeSignature, is_last: bool) -> GrooveBar:
    """Turn a seed into a bar: keep its hands verbatim, ground it with a kick on
    the downbeat, and (on the phrase's last bar) land a kick under the final
    stroke so the fill resolves into the next downbeat."""
    hands = [_clone(h) for h in seed.hands]
    feet = [_clone(f) for f in seed.feet]

    if not any(f.onset == 0 for f in feet):
        feet.append(Hit(onset=Fraction(0), duration=_KICK_DUR, surface=Surface.KICK))
    if is_last and hands:
        land = max(h.onset for h in hands)
        if land > 0 and not any(f.onset == land for f in feet):
            feet.append(Hit(onset=land, duration=_KICK_DUR, surface=Surface.KICK))
    feet.sort(key=lambda h: h.onset)
    return GrooveBar(time_sig=ts, hands=hands, feet=feet)


def seeded_fill_bars(
    ts: TimeSignature, difficulty: Difficulty, num_bars: int, rng: random.Random
) -> list[GrooveBar] | None:
    """A fill built from the seed bank, one distinct seed per bar (no immediate
    repeats within a phrase). Returns None if the meter isn't seedable."""
    if not is_seedable(ts):
        return None
    seeds = _seeds_for(difficulty)
    if not seeds:
        return None

    pool: list[FillSeed] = []
    bars: list[GrooveBar] = []
    for bi in range(num_bars):
        if not pool:
            pool = list(seeds)
        chosen = rng.choice(pool)
        pool.remove(chosen)
        bars.append(_render(chosen, ts, is_last=(bi == num_bars - 1)))
    return bars
