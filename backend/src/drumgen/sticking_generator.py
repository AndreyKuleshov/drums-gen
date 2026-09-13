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

# Selection weight per family for the packer's weighted shuffle. Singles are
# down-weighted so the generator doesn't lean on single strokes; odd groupings and
# paradiddles are favoured.
_FAMILY_WEIGHT: dict[Family, float] = {"singles": 1.0, "odd": 2.6, "paradiddle": 2.6}

# Short label drawn on the bracket over each placed block, parallel to VOCAB.
# Singles get an empty label so they aren't bracketed — the brackets highlight the
# rudiments (odd groupings, paradiddles), not plain single strokes.
_BLOCK_LABEL: dict[Family, tuple[str, ...]] = {
    "singles": ("", "", "", ""),
    "odd": ("3", "5", "7"),
    "paradiddle": ("Para", "Dbl para", "Para-diddle-diddle"),
}

# A packer candidate: the block, its selection weight, and its bracket label.
Candidate = tuple[Block, float, str]

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
    mixed: bool = False
    """Mix 1/8 and 1/16 durations within a bar (per-beat) instead of a uniform
    grid. When true, `subdivision` is ignored (the finest grid is 1/16)."""
    voicing: Literal["snare", "kit", "linear"] = "snare"
    """'snare' = pure sticking on the snare (monophonic Phrase); 'kit' = the same
    sticking orchestrated across the kit with a simultaneous kick foundation
    (polyphonic Groove); 'linear' = orchestrated across the kit as a single line
    where at most one stroke sounds at a time — kick woven in, no simultaneity."""
    seed: int | None = None


def _candidates(req: StickingRequest) -> list[Candidate]:
    """Enabled families' blocks in both orientations (as-is + mirror), each tagged
    with a selection weight and a bracket label."""
    flags = {"singles": req.singles, "odd": req.odd, "paradiddle": req.paradiddle}
    enabled: list[Family] = [fam for fam in _FAMILY_FLAGS if flags[fam]]
    out: list[Candidate] = []
    for fam in enabled:
        weight = _FAMILY_WEIGHT[fam]
        for i, block in enumerate(VOCAB[fam]):
            label = _BLOCK_LABEL[fam][i]
            out.append((block, weight, label))
            out.append((mirror(block), weight, label))
    return out


def _pack(total: int, candidates: list[Candidate], rng: random.Random) -> list[tuple[Block, str]]:
    """Backtracking search for a legal stream of exactly `total` notes, returned as
    the sequence of placed (block, label). Each step orders candidates by a
    weighted shuffle (Efraimidis-Spirakis: key = u**(1/weight)), so higher-weight
    families are tried first — biasing away from single strokes."""
    stream: list[Note] = []
    placed: list[tuple[Block, str]] = []

    def build() -> bool:
        if len(stream) == total:
            return True
        order = sorted(candidates, key=lambda c: rng.random() ** (1.0 / c[1]), reverse=True)
        for block, _weight, label in order:
            if len(stream) + len(block) > total:
                continue
            stream.extend(block)
            if rules_hold(stream):
                placed.append((block, label))
                if build():
                    return True
                placed.pop()
            del stream[len(stream) - len(block) :]
        return False

    if not build():
        raise GenerationError("Could not fill the phrase with the selected families.")
    return placed


# Accents "ride" across the kit: the lead surface advances each beat, so the
# accented melody moves snare -> high -> mid -> low tom.
_LEAD_ORDER = [Surface.SNARE, Surface.TOM_HIGH, Surface.TOM_MID, Surface.TOM_LOW]
_SIXTEENTH = Fraction(1, 16)
_EIGHTH = Fraction(1, 8)

# A rhythm slot is a (onset, duration) pair within a bar; a bar is a list of them.
Slots = list[list[tuple[Fraction, Fraction]]]


_MIXED_MIN_UNIT = _SIXTEENTH  # the fine grid mixed durations are built on


def _mixed_cell(k: int, rng: random.Random) -> list[int]:
    """A random composition of 1s (a 1/16) and 2s (a 1/8) summing to `k` sixteenth
    units — one beat's worth of mixed durations."""
    cell: list[int] = []
    remaining = k
    while remaining > 0:
        piece = 1 if remaining == 1 else rng.choice((1, 2))
        cell.append(piece)
        remaining -= piece
    return cell


def _rhythm_slots(req: StickingRequest, rng: random.Random) -> Slots:
    """Per-bar (onset, duration) slots: uniform at `subdivision`, or — when
    `mixed` — a per-beat random mix of 1/8 and 1/16 notes."""
    ts = req.time_sig
    bar_len = ts.bar_length
    slots: Slots = []
    if req.mixed:
        beat_len = ts.beat_length
        num_beats = int(bar_len / beat_len)
        per_beat = beat_len / _MIXED_MIN_UNIT
        if per_beat.denominator != 1:
            raise GenerationError("Mixed durations need a 1/16-divisible beat.")
        k = int(per_beat)
        for _bar in range(req.num_bars):
            onset = Fraction(0)
            bar: list[tuple[Fraction, Fraction]] = []
            for _beat in range(num_beats):
                for unit in _mixed_cell(k, rng):
                    dur = _MIXED_MIN_UNIT * unit
                    bar.append((onset, dur))
                    onset += dur
            slots.append(bar)
    else:
        sub = req.subdivision
        per_bar = int(bar_len / sub)
        for _bar in range(req.num_bars):
            slots.append([(j * sub, sub) for j in range(per_bar)])
    return slots


def generate_sticking(req: StickingRequest) -> Phrase | Groove:
    candidates = _candidates(req)
    if not candidates:
        raise GenerationError("Enable at least one block family.")

    # Guard on the finest possible grid (1/16 when mixed) before building slots,
    # so pathological meters/subdivisions raise instead of doing unbounded work.
    finest = _SIXTEENTH if req.mixed else req.subdivision
    per_bar_exact = req.time_sig.bar_length / finest
    if per_bar_exact.denominator != 1:
        raise GenerationError("Subdivision must divide the bar into whole notes.")
    max_total = int(per_bar_exact) * req.num_bars
    if max_total > _MAX_NOTES:
        raise GenerationError(
            f"Phrase too large ({max_total} notes); reduce bars or use a coarser subdivision."
        )

    rng = random.Random(req.seed)
    slots = _rhythm_slots(req, rng)
    total = sum(len(bar) for bar in slots)
    placed = _pack(total, candidates, rng)
    stream: list[Note] = [note for block, _label in placed for note in block]
    # Per-note (block-instance-id, label) for the bracket over each placed block.
    note_meta: list[tuple[int, str]] = []
    for block_id, (block, label) in enumerate(placed):
        note_meta.extend((block_id, label) for _ in block)

    ghosts = _ghost_flags(stream)
    if req.voicing == "linear":
        return _orchestrate_linear(stream, slots, req, rng, ghosts)
    if req.voicing == "kit":
        return _orchestrate_kit(stream, slots, req, rng, note_meta, ghosts)
    return _snare_phrase(stream, slots, note_meta, ghosts, req)


def _out_subdivision(req: StickingRequest) -> Fraction:
    """The `subdivision` metadata on the output model — the finest grid used."""
    return _SIXTEENTH if req.mixed else req.subdivision


def _ghost_flags(stream: list[Note]) -> list[bool]:
    """Which strokes are ghost notes. A non-accented stroke is a ghost only when
    it repeats the previous hand — the 2nd of a diddle (double). The alternating
    single taps stay normal, so a pattern reads as a MIX of accents, taps and
    ghosts instead of 'every non-accent is a ghost'."""
    return [
        (not accent) and i > 0 and stream[i - 1][0] == hand
        for i, (hand, accent) in enumerate(stream)
    ]


def _snare_phrase(
    stream: list[Note],
    slots: Slots,
    note_meta: list[tuple[int, str]],
    ghosts: list[bool],
    req: StickingRequest,
) -> Phrase:
    """Pure sticking: every stroke on the snare, monophonic Phrase. Notes are
    grouped (beamed) per beat via `Stroke.group` so a bar of sixteenths reads as
    groups of four; `block`/`block_label` tag each stroke's vocabulary block for
    the labelled bracket over the group. Strokes are accents, ghosts (diddles) or
    plain taps."""
    beat_len = req.time_sig.beat_length
    bars: list[Bar] = []
    idx = 0
    for bar_slots in slots:
        strokes: list[Stroke] = []
        for onset, dur in bar_slots:
            hand, accent = stream[idx]
            block_id, label = note_meta[idx]
            strokes.append(
                Stroke(
                    duration=dur,
                    hand=Hand(hand),
                    accent=accent,
                    ghost=ghosts[idx],
                    group=int(onset / beat_len),
                    block=block_id,
                    block_label=label,
                )
            )
            idx += 1
        bars.append(Bar(time_sig=req.time_sig, strokes=strokes))

    return Phrase(
        time_sig=req.time_sig,
        tempo_bpm=req.tempo_bpm,
        subdivision=_out_subdivision(req),
        accent_mode=AccentMode.RUDIMENT,
        bars=bars,
    )


def _lead_surface(
    onset: Fraction,
    beat_len: Fraction,
    lead_start: int,
    bar: int,
    order: list[Surface] = _LEAD_ORDER,
) -> Surface:
    """Accented lead surface for `onset` — steps through `order` each beat so the
    accents ride across the kit. A shuffled `order` + `lead_start` re-lays the
    same accents onto different drums."""
    beat_i = int(onset / beat_len)
    return order[(beat_i + lead_start + bar) % len(order)]


def _kit_hand_hit(
    onset: Fraction,
    dur: Fraction,
    hand: Hand,
    accent: bool,
    beat_len: Fraction,
    lead_start: int,
    bar: int,
    block: int = -1,
    block_label: str = "",
    lead_order: list[Surface] = _LEAD_ORDER,
    is_ghost: bool = False,
) -> Hit:
    """One hands-voice hit for the kit orchestration: an accent rides the snare/tom
    lead, a non-accent goes to the hi-hat (right hand) or snare (left). Ghost notes
    exist ONLY on the snare AND only for strokes flagged `is_ghost` (the diddles) —
    a plain snare tap or any hi-hat note is not a ghost. `block`/`block_label` carry
    the vocabulary-block tag for the labelled bracket over the group."""
    if accent:
        surface = _lead_surface(onset, beat_len, lead_start, bar, lead_order)
        return Hit(
            onset=onset,
            duration=dur,
            surface=surface,
            hand=hand,
            accent=True,
            block=block,
            block_label=block_label,
        )
    surface = Surface.HIHAT if hand is Hand.R else Surface.SNARE
    return Hit(
        onset=onset,
        duration=dur,
        surface=surface,
        hand=hand,
        ghost=is_ghost and surface is Surface.SNARE,
        block=block,
        block_label=block_label,
    )


def _orchestrate_kit(
    stream: list[Note],
    slots: Slots,
    req: StickingRequest,
    rng: random.Random,
    note_meta: list[tuple[int, str]],
    ghosts: list[bool],
) -> Groove:
    """Accents ride snare/toms (moving a step down the kit each beat), ghosts split
    to hi-hat (right hand) and snare (left), and a simultaneous kick foundation
    (downbeat + sampled syncopations + landing) grounds it. Polyphonic Groove."""
    ts = req.time_sig
    beat_len = ts.beat_length
    lead_start = rng.randrange(len(_LEAD_ORDER))
    # Notate the kick at the pattern's own note value so it doesn't read as a
    # faster 16th under an 1/8 pattern.
    kick_dur = _out_subdivision(req)

    eighth_grid: list[Fraction] = []
    pos = _EIGHTH
    while pos < ts.bar_length:
        eighth_grid.append(pos)
        pos += _EIGHTH

    bars: list[GrooveBar] = []
    idx = 0
    for b, bar_slots in enumerate(slots):
        hands: list[Hit] = []
        for onset, dur in bar_slots:
            hand_char, accent = stream[idx]
            block_id, label = note_meta[idx]
            hit = _kit_hand_hit(
                onset,
                dur,
                Hand(hand_char),
                accent,
                beat_len,
                lead_start,
                b,
                block_id,
                label,
                is_ghost=ghosts[idx],
            )
            hands.append(hit)
            idx += 1

        feet: list[Hit] = [Hit(onset=Fraction(0), duration=kick_dur, surface=Surface.KICK)]
        count = min(rng.randint(1, 3), len(eighth_grid))
        for onset in rng.sample(eighth_grid, count):
            feet.append(Hit(onset=onset, duration=kick_dur, surface=Surface.KICK))
        if b == req.num_bars - 1 and bar_slots:
            land = bar_slots[-1][0]
            if land > 0 and all(f.onset != land for f in feet):
                feet.append(Hit(onset=land, duration=kick_dur, surface=Surface.KICK))
        feet.sort(key=lambda h: h.onset)
        bars.append(GrooveBar(time_sig=ts, hands=hands, feet=feet))

    return Groove(
        time_sig=ts, tempo_bpm=req.tempo_bpm, subdivision=_out_subdivision(req), bars=bars
    )


def _orchestrate_linear(
    stream: list[Note],
    slots: Slots,
    req: StickingRequest,
    rng: random.Random,
    ghosts: list[bool],
) -> Groove:
    """A linear fill: one line across the whole kit with AT MOST ONE stroke per
    onset. Accents ride snare/toms, ghosts land on hi-hat/snare, and some ghosts
    are woven in as a kick (a foot, not a hand) — so hands and feet never share
    an onset and nothing sounds simultaneously."""
    ts = req.time_sig
    beat_len = ts.beat_length
    lead_start = rng.randrange(len(_LEAD_ORDER))

    bars: list[GrooveBar] = []
    idx = 0
    for b, bar_slots in enumerate(slots):
        hands: list[Hit] = []
        feet: list[Hit] = []
        for onset, dur in bar_slots:
            hand_char, accent = stream[idx]
            is_ghost = ghosts[idx]
            idx += 1
            hand = Hand(hand_char)
            if not accent and rng.random() < 0.3:
                # A ghost becomes a kick — played by the foot, replacing the hand
                # stroke, so only one voice sounds at this onset.
                feet.append(Hit(onset=onset, duration=dur, surface=Surface.KICK))
            elif accent:
                surface = _lead_surface(onset, beat_len, lead_start, b)
                hands.append(
                    Hit(onset=onset, duration=dur, surface=surface, hand=hand, accent=True)
                )
            else:
                surface = Surface.HIHAT if hand is Hand.R else Surface.SNARE
                # Ghost notes only exist on the snare, and only for diddles.
                hands.append(
                    Hit(
                        onset=onset,
                        duration=dur,
                        surface=surface,
                        hand=hand,
                        ghost=is_ghost and surface is Surface.SNARE,
                    )
                )
        bars.append(GrooveBar(time_sig=ts, hands=hands, feet=feet))

    return Groove(
        time_sig=ts, tempo_bpm=req.tempo_bpm, subdivision=_out_subdivision(req), bars=bars
    )


def revoice_kit(phrase: Phrase, seed: int | None = None) -> Groove:
    """Re-voice an existing snare Phrase across the kit WITHOUT regenerating it:
    the same sticking, accents ride the snare/tom lead, non-accents split to
    hi-hat (right) / snare (left), ghosts stay on the snare. No kick — this is a
    hands-only re-lay of a sticking, not a full groove.

    With `seed=None` the lead is fixed (lead 0, natural order) so the first
    toggle to the kit is stable. A `seed` shuffles the lead order and starting
    drum, so the SAME sticking lands on different drums — that powers the
    'shuffle the kit layout' button."""
    ts = phrase.time_sig
    beat_len = ts.beat_length
    if seed is None:
        lead_start, order = 0, _LEAD_ORDER
    else:
        rng = random.Random(seed)
        order = list(_LEAD_ORDER)
        rng.shuffle(order)
        lead_start = rng.randrange(len(order))
    bars: list[GrooveBar] = []
    for b, bar in enumerate(phrase.bars):
        hands: list[Hit] = []
        onset = Fraction(0)
        for s in bar.strokes:
            hands.append(
                _kit_hand_hit(
                    onset,
                    s.duration,
                    s.hand,
                    s.accent,
                    beat_len,
                    lead_start,
                    b,
                    s.block,
                    s.block_label,
                    order,
                    s.ghost,
                )
            )
            onset += s.duration
        bars.append(GrooveBar(time_sig=ts, hands=hands, feet=[]))
    return Groove(
        time_sig=ts, tempo_bpm=phrase.tempo_bpm, subdivision=phrase.subdivision, bars=bars
    )
