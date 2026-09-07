"""Pattern Generator 2.0 — sticking-block phrase generator.

Packs a small vocabulary of rudimental blocks (accented singles, odd 3/5/7
groupings, paradiddles) edge-to-edge to fill N bars, enforcing two rules across
the whole stream:

  1. Adjacent accents alternate hands.
  2. No more than two consecutive ghost notes on the same hand.

Every note is either an accent (uppercase) or a ghost (lowercase). Blocks are
stored canonically R-lead; the L-lead form is `mirror()`. Output is the existing
monophonic `Phrase` model, so it renders and plays through the same components.
Provides `StickingRequest` and `generate_sticking`, a seeded backtracking packer
that fills N bars and returns a `Phrase`.
"""

import random
from collections.abc import Sequence
from typing import Literal

from pydantic import BaseModel, Field

from drumgen.domain.enums import AccentMode, Hand
from drumgen.domain.fractions import FractionField
from drumgen.domain.models import Bar, Phrase, Stroke, TimeSignature
from drumgen.generator import GenerationError

# A note is (hand, is_accent); a ghost is simply not-accent.
Note = tuple[str, bool]
Block = tuple[Note, ...]
Family = Literal["singles", "odd", "paradiddle"]


def _parse(spec: str) -> Block:
    """`"Rll"` -> ((R,accent),(L,ghost),(L,ghost)). Uppercase = accent."""
    return tuple((ch.upper(), ch.isupper()) for ch in spec)


VOCAB: dict[Family, tuple[Block, ...]] = {
    "singles": tuple(_parse(s) for s in ("R", "RL", "RLR", "RLRL")),
    "odd": tuple(_parse(s) for s in ("Rll", "RlRll", "RlRlRll")),
    "paradiddle": tuple(_parse(s) for s in ("Rlrr", "RlRlrr", "Rlrrll")),
}


def mirror(block: Block) -> Block:
    """Swap every R<->L; accents unchanged."""
    return tuple(("L" if hand == "R" else "R", accent) for hand, accent in block)


def rules_hold(stream: Sequence[Note]) -> bool:
    """Both hard rules over the stream."""
    # Rule 1: two adjacent accents must be different hands.
    for i in range(1, len(stream)):
        hand, accent = stream[i]
        prev_hand, prev_accent = stream[i - 1]
        if accent and prev_accent and hand == prev_hand:
            return False
    # Rule 2: at most two consecutive same-hand ghosts.
    run_hand: str | None = None
    run = 0
    for hand, accent in stream:
        if accent:
            run_hand, run = None, 0
            continue
        if hand == run_hand:
            run += 1
        else:
            run_hand, run = hand, 1
        if run > 2:
            return False
    return True


_FAMILY_FLAGS: tuple[Family, ...] = ("singles", "odd", "paradiddle")

# Upper bound on notes in one phrase. Bounds the backtracking depth well under
# Python's recursion limit and rejects pathological meters/subdivisions with a
# controlled GenerationError instead of an uncaught RecursionError. 1024 covers
# the supported v1 space (e.g. 4/4 at 1/16 for 64 bars = 1024 notes).
_MAX_NOTES = 1024


class StickingRequest(BaseModel):
    time_sig: TimeSignature
    num_bars: int = Field(ge=1, le=64)
    subdivision: FractionField
    tempo_bpm: int = Field(ge=1)
    singles: bool = True
    odd: bool = True
    paradiddle: bool = True
    seed: int | None = None


def _candidates(req: StickingRequest) -> list[Block]:
    """Enabled families' blocks in both orientations (as-is + mirror)."""
    flags = {"singles": req.singles, "odd": req.odd, "paradiddle": req.paradiddle}
    enabled: list[Family] = [fam for fam in _FAMILY_FLAGS if flags[fam]]
    blocks: list[Block] = []
    for fam in enabled:
        for block in VOCAB[fam]:
            blocks.append(block)
            blocks.append(mirror(block))
    return blocks


def _pack(total: int, candidates: list[Block], rng: random.Random) -> list[Note]:
    """Backtracking search for a legal note stream of exactly `total` notes."""

    def build(stream: list[Note]) -> list[Note] | None:
        if len(stream) == total:
            return stream
        order = candidates[:]
        rng.shuffle(order)
        for block in order:
            if len(stream) + len(block) > total:
                continue
            nxt = stream + list(block)
            if not rules_hold(nxt):
                continue
            result = build(nxt)
            if result is not None:
                return result
        return None

    packed = build([])
    if packed is None:
        raise GenerationError("Could not fill the phrase with the selected families.")
    return packed


def generate_sticking(req: StickingRequest) -> Phrase:
    candidates = _candidates(req)
    if not candidates:
        raise GenerationError("Enable at least one block family.")

    bar_len = req.time_sig.bar_length
    per_bar_exact = bar_len / req.subdivision
    if per_bar_exact.denominator != 1:
        raise GenerationError("Subdivision must divide the bar into whole notes.")
    per_bar = int(per_bar_exact)
    total = per_bar * req.num_bars

    if total > _MAX_NOTES:
        raise GenerationError(
            f"Phrase too large ({total} notes); reduce bars or use a coarser subdivision."
        )

    rng = random.Random(req.seed)
    stream = _pack(total, candidates, rng)

    bars: list[Bar] = []
    for b in range(req.num_bars):
        chunk = stream[b * per_bar : (b + 1) * per_bar]
        strokes = [
            Stroke(
                duration=req.subdivision,
                hand=Hand(hand),
                accent=accent,
                ghost=not accent,
            )
            for hand, accent in chunk
        ]
        bars.append(Bar(time_sig=req.time_sig, strokes=strokes))

    return Phrase(
        time_sig=req.time_sig,
        tempo_bpm=req.tempo_bpm,
        subdivision=req.subdivision,
        accent_mode=AccentMode.RUDIMENT,
        bars=bars,
    )
