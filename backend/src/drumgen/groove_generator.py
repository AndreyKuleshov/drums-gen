"""Deterministic full-kit groove generator (Pattern mode).

Built beat-relative so it works in any meter: the hi-hat subdivides each beat,
and kick/snare placement uses per-difficulty rules expressed in beats. Hi-hat
and snare are both HANDS (hi-hat = right, snare = left) so they never contend
for the same hand; the kick is an independent FEET voice.
"""

import random
from fractions import Fraction
from typing import Literal

from pydantic import BaseModel, Field

from drumgen.catalog import MVP_CATALOG, RudimentTemplate
from drumgen.domain.enums import Articulation, Difficulty, Hand, Surface
from drumgen.domain.fractions import FractionField
from drumgen.domain.groove import Groove, GrooveBar, Hit
from drumgen.domain.models import TimeSignature

# Absolute note-value grids (whole-note units). Using absolute 1/8 and 1/16
# rather than beat-relative subdivisions keeps every onset on a 1/16 grid, which
# makes the notation render with standard durations in ANY meter (incl.
# compound), and gives musically-correct eighth-note hi-hats regardless of meter.
_EIGHTH = Fraction(1, 8)
_SIXTEENTH = Fraction(1, 16)
_THIRTYSECOND = Fraction(1, 32)

_TIER: dict[Difficulty, int] = {Difficulty.BEGINNER: 0, Difficulty.MID: 1, Difficulty.PRO: 2}
# Toms descend high -> mid -> low; fills move accents around them.
_TOMS = [Surface.TOM_HIGH, Surface.TOM_MID, Surface.TOM_LOW]


class GrooveRequest(BaseModel):
    time_sig: TimeSignature
    num_bars: int = Field(ge=1, le=64)
    tempo_bpm: int = Field(ge=1)
    difficulty: Difficulty = Difficulty.BEGINNER
    style: Literal["groove", "fill", "phrase"] = "groove"
    hands: Literal["straight", "rudiment"] = "straight"
    """Groove hands voice: 'straight' = steady hi-hat + backbeat snare;
    'rudiment' = a rudiment orchestrated between hi-hat and snare."""
    subdivision: FractionField = _EIGHTH
    """Max hi-hat subdivision: 1/8 = up to eighth hats, 1/16 = up to sixteenth hats."""
    feel: Literal["straight", "triplet", "mixed", "authentic"] = "straight"
    """Rhythmic style within the subdivision ceiling: 'straight' = even, 'mixed' =
    a free mix of note values per beat. (Triplet needs triplet notation — TODO.)"""
    seed: int | None = None


def _beats(ts: TimeSignature) -> tuple[Fraction, int]:
    beat = ts.beat_length
    return beat, int(ts.bar_length / beat)


# The hi-hat GRID is set by the Subdivision control (base): 1/8 = eighth hats,
# 1/16 = sixteenth hats. Difficulty controls everything ELSE (kick syncopation,
# ghosts, open hats, toms) — not the grid.
_OPEN_HAT_PROB = {Difficulty.BEGINNER: 0.15, Difficulty.MID: 0.5, Difficulty.PRO: 0.85}


def _hihat(
    ts: TimeSignature,
    difficulty: Difficulty,
    rng: random.Random,
    base: Fraction = _EIGHTH,
    feel: str = "straight",
) -> list[Hit]:
    beat, num_beats = _beats(ts)
    eighth = _EIGHTH
    bar = ts.bar_length

    # Hi-hat grid on the right hand. Subdivision is the ceiling; Feel is the style.
    onsets: list[Fraction] = []
    if feel == "mixed":
        # A free mix: each beat gets its own subdivision (no finer than `base`).
        steps = [s for s in (beat, eighth, _SIXTEENTH) if s >= base]
        for b in range(num_beats):
            step = rng.choice(steps)
            o = b * beat
            while o < (b + 1) * beat and o < bar:
                onsets.append(o)
                o += step
    else:  # straight (triplet/authentic fall back to straight until triplet notation)
        o = Fraction(0)
        while o < bar:
            onsets.append(o)
            o += base

    # An open hi-hat on the last eighth of the bar.
    open_onset = bar - eighth if rng.random() < _OPEN_HAT_PROB[difficulty] else None

    hits: list[Hit] = []
    for on in onsets:
        is_open = on == open_onset
        on_beat = (on / beat).denominator == 1
        hits.append(
            Hit(
                onset=on,
                duration=beat if is_open else eighth,
                surface=Surface.HIHAT_OPEN if is_open else Surface.HIHAT,
                hand=Hand.R,
                accent=is_open or (difficulty is not Difficulty.BEGINNER and on_beat),
            )
        )
    return hits


_GHOST_COUNT = {
    Difficulty.BEGINNER: (0, 1),
    Difficulty.MID: (1, 2),
    Difficulty.PRO: (2, 3),
}


def _snare(ts: TimeSignature, difficulty: Difficulty, rng: random.Random) -> list[Hit]:
    beat, num_beats = _beats(ts)
    eighth = _EIGHTH
    hits: list[Hit] = []

    # Backbeats: the odd-indexed beats (2 & 4 in common time), left hand.
    backbeats = [b for b in range(num_beats) if b % 2 == 1] or [num_beats - 1]
    for b in backbeats:
        hits.append(
            Hit(onset=b * beat, duration=eighth, surface=Surface.SNARE, hand=Hand.L, accent=True)
        )

    # Ghost notes on off-beat eighths (never on a backbeat) — more the harder the level.
    taken = {h.onset for h in hits}
    candidates = [b * beat + eighth for b in range(num_beats) if b * beat + eighth < ts.bar_length]
    rng.shuffle(candidates)
    lo, hi = _GHOST_COUNT[difficulty]
    for on in candidates[: rng.randint(lo, hi)]:
        if on not in taken:
            hits.append(
                Hit(onset=on, duration=eighth, surface=Surface.SNARE, hand=Hand.L, ghost=True)
            )
    return hits


# Number of syncopated "and-of-the-beat" kicks beyond the 1 & mid-bar foundation.
_KICK_ANDS = {
    Difficulty.BEGINNER: (1, 2),
    Difficulty.MID: (2, 3),
    Difficulty.PRO: (1, 2),
}


def _kick(ts: TimeSignature, difficulty: Difficulty, rng: random.Random) -> list[Hit]:
    beat, num_beats = _beats(ts)
    eighth = _EIGHTH
    sixteenth = _SIXTEENTH
    bar = ts.bar_length

    # Foundation: beat 1 and the mid-bar beat (varied with syncopations per level).
    onsets: set[Fraction] = {Fraction(0)}
    mid = num_beats // 2
    if mid > 0:
        onsets.add(mid * beat)

    ands = [b * beat + eighth for b in range(num_beats) if b * beat + eighth < bar]
    rng.shuffle(ands)
    lo, hi = _KICK_ANDS[difficulty]
    onsets |= set(ands[: rng.randint(lo, hi)])

    hits = [Hit(onset=o, duration=eighth, surface=Surface.KICK) for o in sorted(onsets)]

    if difficulty is Difficulty.PRO and rng.random() < 0.7:
        # Double-pedal (kardan): a short 16th foot-run, alternating feet — placed on
        # a RANDOM beat (not always the last) and of varied length, so it doesn't
        # always end the bar with the same four sixteenths.
        existing = {h.onset for h in hits}
        run_beat = rng.randrange(num_beats)
        run_len = rng.choice([2, 3, 4])
        foot = Hand.R
        for k in range(run_len):
            o = run_beat * beat + k * sixteenth
            if o < bar and o not in existing:
                hits.append(Hit(onset=o, duration=sixteenth, surface=Surface.KICK, hand=foot))
            foot = foot.other()
        hits.sort(key=lambda h: h.onset)

    return hits


def _sprinkle_toms(hands: list[Hit], rng: random.Random) -> list[Hit]:
    """Fold one or two unaccented hi-hat strokes into tom hits (same hand) — a
    linear splash of colour that lifts the advanced groove above the mid one."""
    idxs = [i for i, h in enumerate(hands) if h.surface is Surface.HIHAT and not h.accent]
    if not idxs:
        return hands
    rng.shuffle(idxs)
    chosen = set(idxs[: min(len(idxs), rng.randint(1, 2))])
    out: list[Hit] = []
    tom_i = 0
    for i, h in enumerate(hands):
        if i in chosen:
            out.append(
                Hit(
                    onset=h.onset,
                    duration=h.duration,
                    surface=_TOMS[tom_i % len(_TOMS)],
                    hand=h.hand,
                    accent=True,
                )
            )
            tom_i += 1
        else:
            out.append(h)
    return out


# ---------- rudiment orchestration (hands = rudiment, and fills) -------------


def _pick_template(difficulty: Difficulty, rng: random.Random) -> RudimentTemplate:
    """A rudiment within the difficulty tier that has accents (so orchestration
    is musical) and is longer than a single stroke."""
    tier = _TIER[difficulty]
    pool = [
        t
        for t in MVP_CATALOG
        if _TIER[t.difficulty] <= tier
        and len(t.elements) >= 2
        and any(e.accent for e in t.elements)
    ]
    if not pool:
        pool = [t for t in MVP_CATALOG if len(t.elements) >= 2]
    return rng.choice(pool)


def _cap_runs(seq: list[tuple[Hand, bool]]) -> list[tuple[Hand, bool]]:
    """Enforce the sticking rule: never more than two strokes in a row with the
    same hand. A would-be third same-hand stroke is flipped to the other hand."""
    out: list[tuple[Hand, bool]] = []
    prev: Hand | None = None
    run = 0
    for hand, accent in seq:
        if hand == prev:
            run += 1
        else:
            prev, run = hand, 1
        if run > 2:
            hand = hand.other()
            prev, run = hand, 1
        out.append((hand, accent))
    return out


def _stream(difficulty: Difficulty, cells: int, rng: random.Random) -> list[tuple[Hand, bool]]:
    """A (hand, accent) stream of `cells` steps built from a chosen rudiment.

    Templates store a single-lead sticking (e.g. paradiddle = RLRR). Repeating it
    verbatim would break the max-two rule at the seam (RLRR|RLRR -> RRR), so each
    repetition mirrors the hands (RLRR then LRLL) — the way these are practised —
    and a final cap guarantees no run exceeds two."""
    base = [(e.hand, e.accent) for e in _pick_template(difficulty, rng).elements]
    seq: list[tuple[Hand, bool]] = []
    rep = 0
    while len(seq) < cells:
        mirror = rep % 2 == 1
        seq.extend((h.other() if mirror else h, a) for h, a in base)
        rep += 1
    return _cap_runs(seq[:cells])


_RUDIMENT_GHOST_DENSITY = {
    Difficulty.BEGINNER: 0.2,
    Difficulty.MID: 0.4,
    Difficulty.PRO: 0.55,
}


def _hands_rudiment(
    ts: TimeSignature,
    difficulty: Difficulty,
    rng: random.Random,
    base: Fraction = _SIXTEENTH,
    feel: str = "straight",
) -> list[Hit]:
    """A GROOVE (not an exercise): a steady hi-hat ostinato (at the subdivision, in
    the chosen feel) + backbeat snare, with rudiment-derived ghost notes filling the
    snare hand between the backbeats. Beat 1 is hi-hat + kick, never a bare snare."""
    beat, num_beats = _beats(ts)
    hits = _hihat(ts, difficulty, rng, base, feel)  # hi-hat ostinato (right hand)

    backbeats = {b * beat for b in range(num_beats) if b % 2 == 1} or {(num_beats - 1) * beat}
    for onset in backbeats:
        hits.append(
            Hit(onset=onset, duration=_EIGHTH, surface=Surface.SNARE, hand=Hand.L, accent=True)
        )

    # Rudiment left-hand strokes become snare ghosts — never on the downbeat or a
    # backbeat — so the groove has paradiddle-flavoured ghost work, not a drum lesson.
    cells = round(ts.bar_length / base)
    density = _RUDIMENT_GHOST_DENSITY[difficulty]
    for i, (hand, accent) in enumerate(_stream(difficulty, cells, rng)):
        onset = i * base
        if onset == 0 or onset in backbeats:
            continue
        if hand is Hand.L and not accent and rng.random() < density:
            hits.append(
                Hit(onset=onset, duration=base, surface=Surface.SNARE, hand=Hand.L, ghost=True)
            )
    return hits


# ---------- fills: musical beat-by-beat composition ----------
#
# A fill is composed ONE BEAT AT A TIME from a small vocabulary of rhythmic cells,
# so consecutive bars differ (no "identical phrases"). Density builds toward the
# end; strokes move AROUND the kit (snare + toms with hi-hat mixed in to break up
# the toms); accents can be flammed; and the fill lands with a kick on the last
# stroke.

# A fill moves around the kit rather than sitting on one drum.
_KIT_PATH = [Surface.SNARE, Surface.TOM_HIGH, Surface.TOM_MID, Surface.TOM_LOW]


def _surface_plan(total: int, rng: random.Random) -> list[Surface]:
    """A per-beat lead-drum plan cycling snare -> high -> mid -> low, lingering 1-2
    beats on each drum so the fill isn't mechanically regular (one drum per beat)."""
    beats = max(1, total // 8)
    plan: list[Surface] = []
    i = 0
    while len(plan) < beats:
        plan.extend([_KIT_PATH[i % len(_KIT_PATH)]] * rng.randint(1, 2))
        i += 1
    return plan[:beats]


# Rhythmic cells for one beat (durations in 32nds, summing to 8), by density.
_CELLS: dict[str, list[list[int]]] = {
    "simple": [[8], [4, 4], [4, 2, 2], [2, 2, 4]],
    "med": [[2, 2, 2, 2], [4, 2, 2], [2, 2, 4], [2, 4, 2], [4, 4]],
    "dense": [[2, 2, 2, 2], [1, 1, 2, 2, 2], [2, 2, 1, 1, 2], [1, 1, 1, 1, 4]],
    "burst": [[1, 1, 1, 1, 1, 1, 1, 1], [1, 1, 1, 1, 4], [4, 1, 1, 1, 1], [2, 2, 1, 1, 1, 1]],
}


def _pick_cell(pos: float, difficulty: Difficulty, rng: random.Random) -> list[int]:
    """A beat's rhythm, denser as the fill builds toward its landing."""
    if pos >= 0.82:
        key = "burst" if difficulty is not Difficulty.BEGINNER else "dense"
    elif pos >= 0.5:
        key = "dense" if difficulty is Difficulty.PRO else "med"
    else:
        key = "simple" if difficulty is Difficulty.BEGINNER else "med"
    return rng.choice(_CELLS[key])


def _fill_bars(
    ts: TimeSignature, difficulty: Difficulty, num_bars: int, rng: random.Random
) -> list[GrooveBar]:
    """A musical kit fill composed beat by beat: varied rhythm (so bars differ),
    strokes moving around snare + toms with hi-hat mixed in, accents optionally
    flammed, building into a descending landing grounded by kick."""
    step = _THIRTYSECOND
    _, num_beats = _beats(ts)
    bpb = num_beats * 8  # 32nds per bar
    total = num_bars * bpb
    total_beats = num_bars * num_beats
    plan = _surface_plan(total, rng)
    ornament = difficulty is not Difficulty.BEGINNER
    hihat_ok = difficulty is not Difficulty.BEGINNER  # beginner fills stay on drums

    hands: list[list[Hit]] = [[] for _ in range(num_bars)]
    hand = Hand.R
    prev: list[int] | None = None
    last_onset = 0
    for beat in range(total_beats):
        pos = beat / max(1, total_beats - 1)
        cell = _pick_cell(pos, difficulty, rng)
        if cell == prev and rng.random() < 0.6:  # avoid literal repeats (motifs still ok)
            cell = _pick_cell(pos, difficulty, rng)
        prev = cell
        base = beat * 8
        bi = base // bpb
        lead = plan[min(beat, len(plan) - 1)]
        last_beat = beat == total_beats - 1
        o = base
        for j, d in enumerate(cell):
            head = j == 0
            surface = lead
            accent = head
            ghost = False
            art = Articulation.NORMAL
            if last_beat:
                # Descending tom cascade into the landing.
                surface = _TOMS[min(len(_TOMS) - 1, j * len(_TOMS) // max(1, len(cell)))]
                accent = True
            elif head:
                if ornament and surface in _TOMS and rng.random() < 0.3:
                    art = Articulation.FLAM if rng.random() < 0.8 else Articulation.DRAG
            else:
                r = rng.random()
                if hihat_ok and r < 0.3:
                    surface, accent = Surface.HIHAT, False  # hi-hat breaks up the toms
                elif r < 0.55:
                    surface, ghost = Surface.SNARE, True  # ghost note
                else:
                    surface = lead if lead in _TOMS else Surface.SNARE
            hands[bi].append(
                Hit(
                    onset=(o - bi * bpb) * step,
                    duration=d * step,
                    surface=surface,
                    hand=hand,
                    accent=accent and not ghost,
                    ghost=ghost,
                    articulation=art,
                )
            )
            hand = hand.other()
            last_onset = o
            o += d

    bars: list[GrooveBar] = []
    for bi in range(num_bars):
        feet: list[Hit] = [Hit(onset=Fraction(0), duration=_SIXTEENTH, surface=Surface.KICK)]
        if bi == num_bars - 1:  # land the fill with a kick under the final stroke
            land = (last_onset - bi * bpb) * step
            if land > 0:
                feet.append(Hit(onset=land, duration=_SIXTEENTH, surface=Surface.KICK))
        bars.append(GrooveBar(time_sig=ts, hands=hands[bi], feet=feet))
    return bars


def _groove_bar(
    ts: TimeSignature,
    difficulty: Difficulty,
    hands_mode: str,
    base: Fraction,
    feel: str,
    rng: random.Random,
) -> GrooveBar:
    """One bar of straight/rudiment groove (hi-hat + snare + kick, toms on advanced)."""
    if hands_mode == "rudiment":
        hands = _hands_rudiment(ts, difficulty, rng, base, feel)
    else:
        hands = [*_hihat(ts, difficulty, rng, base, feel), *_snare(ts, difficulty, rng)]
        # Advanced folds a couple of toms into the ostinato for extra colour.
        if difficulty is Difficulty.PRO:
            hands = _sprinkle_toms(hands, rng)
    return GrooveBar(time_sig=ts, hands=hands, feet=_kick(ts, difficulty, rng))


def generate_groove(req: GrooveRequest) -> Groove:
    rng = random.Random(req.seed)

    if req.style == "fill":
        bars = _fill_bars(req.time_sig, req.difficulty, req.num_bars, rng)
        subdivision: FractionField = _SIXTEENTH
    elif req.style == "phrase":
        # A 4-bar phrase: groove, groove, groove, FILL — repeating. The fill lands
        # on the downbeat of the next phrase.
        bars: list[GrooveBar] = []
        for i in range(req.num_bars):
            if (i + 1) % 4 == 0:
                bars.extend(_fill_bars(req.time_sig, req.difficulty, 1, rng))
            else:
                bars.append(
                    _groove_bar(
                        req.time_sig, req.difficulty, req.hands, req.subdivision, req.feel, rng
                    )
                )
        subdivision = req.subdivision
    else:  # groove
        bars = [
            _groove_bar(req.time_sig, req.difficulty, req.hands, req.subdivision, req.feel, rng)
            for _ in range(req.num_bars)
        ]
        subdivision = req.subdivision

    return Groove(
        time_sig=req.time_sig, tempo_bpm=req.tempo_bpm, subdivision=subdivision, bars=bars
    )
