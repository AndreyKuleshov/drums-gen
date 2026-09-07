"""Pattern Generator 2.0 — sticking-block phrase generator.

Packs a small vocabulary of rudimental blocks (accented singles, odd 3/5/7
groupings, paradiddles) edge-to-edge to fill N bars, enforcing two rules across
the whole stream:

  1. Adjacent accents alternate hands.
  2. No more than two consecutive strokes on the same hand (accents and ghosts
     alike) — you can't play three in a row with one hand.

Every note is either an accent (uppercase) or a ghost (lowercase). Blocks are
stored canonically R-lead; the L-lead form is `mirror()`. Output is the existing
monophonic `Phrase` model, so it renders and plays through the same components.
Provides `StickingRequest` and `generate_sticking`, a seeded backtracking packer
that fills N bars and returns a `Phrase`.
"""

import random
from collections.abc import Sequence
from fractions import Fraction
from typing import Literal

from pydantic import BaseModel, Field

from drumgen.domain.enums import AccentMode, Hand, Surface
from drumgen.domain.fractions import FractionField
from drumgen.domain.groove import Groove, GrooveBar, Hit
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
    # Rule 2: no more than two consecutive strokes on the SAME HAND — counting
    # accents and ghosts alike. Three in a row can't be played by one hand, so a
    # same-hand accent must not abut two same-hand ghosts (or vice versa). This is
    # stricter than a ghosts-only cap and closes the block-seam case where two
    # same-hand ghosts ending one block meet a same-hand accent starting the next.
    run_hand: str | None = None
    run = 0
    for hand, _accent in stream:
        if hand == run_hand:
            run += 1
        else:
            run_hand, run = hand, 1
        if run > 2:
            return False
    return True


_FAMILY_FLAGS: tuple[Family, ...] = ("singles", "odd", "paradiddle")

# Hard ceiling on notes per phrase. Turns pathological meters/subdivisions into a
# controlled GenerationError instead of unbounded work. Note: this bounds total
# work, NOT recursion depth directly — _pack recurses once per placed block, so
# worst-case depth is `total`. In practice the packer favours multi-note blocks
# so realistic depth stays a few hundred at the 1024 ceiling; if the vocabulary
# or subdivisions ever change, re-check depth vs. the recursion limit here.
# 1024 covers the supported v1 space (4/4 at 1/16 for 64 bars = 1024 notes).
_MAX_NOTES = 1024


class StickingRequest(BaseModel):
    time_sig: TimeSignature
    num_bars: int = Field(ge=1, le=64)
    subdivision: FractionField
    tempo_bpm: int = Field(ge=1)
    singles: bool = True
    odd: bool = True
    paradiddle: bool = True
    voicing: Literal["snare", "kit"] = "snare"
    """'snare' = pure sticking on the snare (monophonic Phrase); 'kit' = the same
    sticking orchestrated across the kit — accents ride snare/toms, ghosts split
    to hi-hat (right hand) and snare (left), kick woven underneath (Groove)."""
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


# Accents "ride" across the kit: the lead surface advances each beat, so the
# accented melody moves snare -> high -> mid -> low tom.
_LEAD_ORDER = [Surface.SNARE, Surface.TOM_HIGH, Surface.TOM_MID, Surface.TOM_LOW]
_KICK_DUR = Fraction(1, 16)


def generate_sticking(req: StickingRequest) -> Phrase | Groove:
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

    if req.voicing == "kit":
        return _orchestrate_kit(stream, per_bar, req, rng)
    return _snare_phrase(stream, per_bar, req)


def _snare_phrase(stream: list[Note], per_bar: int, req: StickingRequest) -> Phrase:
    """Pure sticking: every stroke on the snare, monophonic Phrase."""
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


def _orchestrate_kit(
    stream: list[Note], per_bar: int, req: StickingRequest, rng: random.Random
) -> Groove:
    """Orchestrate the sticking across the kit: accents ride snare/toms (moving a
    step down the kit each beat), ghosts split to hi-hat (right hand) and snare
    (left hand), and a kick foundation (1 & 3) grounds it with a landing kick
    under the final stroke. The R/L hand sequence and its two rules are preserved
    exactly — only the surface each stroke lands on changes."""
    ts = req.time_sig
    sub = req.subdivision
    beat_len = ts.beat_length
    num_beats = max(1, int(ts.bar_length / beat_len))
    notes_per_beat = max(1, per_bar // num_beats)
    lead_start = rng.randrange(len(_LEAD_ORDER))

    bars: list[GrooveBar] = []
    for b in range(req.num_bars):
        chunk = stream[b * per_bar : (b + 1) * per_bar]
        hands: list[Hit] = []
        for j, (hand_char, accent) in enumerate(chunk):
            hand = Hand(hand_char)
            onset = j * sub
            if accent:
                beat_i = j // notes_per_beat
                surface = _LEAD_ORDER[(beat_i + lead_start + b) % len(_LEAD_ORDER)]
                hands.append(
                    Hit(onset=onset, duration=sub, surface=surface, hand=hand, accent=True)
                )
            else:
                surface = Surface.HIHAT if hand is Hand.R else Surface.SNARE
                hands.append(Hit(onset=onset, duration=sub, surface=surface, hand=hand, ghost=True))

        # Kick foundation on beats 1 & 3, plus a landing kick under the last
        # stroke of the phrase's final bar.
        feet: list[Hit] = [Hit(onset=Fraction(0), duration=_KICK_DUR, surface=Surface.KICK)]
        if num_beats >= 4:
            mid = (num_beats // 2) * beat_len
            feet.append(Hit(onset=mid, duration=_KICK_DUR, surface=Surface.KICK))
        if b == req.num_bars - 1 and chunk:
            land = (len(chunk) - 1) * sub
            if land > 0 and all(f.onset != land for f in feet):
                feet.append(Hit(onset=land, duration=_KICK_DUR, surface=Surface.KICK))
        feet.sort(key=lambda h: h.onset)
        bars.append(GrooveBar(time_sig=ts, hands=hands, feet=feet))

    return Groove(
        time_sig=ts,
        tempo_bpm=req.tempo_bpm,
        subdivision=sub,
        bars=bars,
    )
