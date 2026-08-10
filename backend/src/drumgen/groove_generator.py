"""Deterministic full-kit groove generator (Pattern mode).

Built beat-relative so it works in any meter: the hi-hat subdivides each beat,
and kick/snare placement uses per-difficulty rules expressed in beats. Hi-hat
and snare are both HANDS (hi-hat = right, snare = left) so they never contend
for the same hand; the kick is an independent FEET voice.
"""

import random
from fractions import Fraction

from pydantic import BaseModel, Field

from drumgen.domain.enums import Difficulty, Hand, Surface
from drumgen.domain.fractions import FractionField
from drumgen.domain.groove import Groove, GrooveBar, Hit
from drumgen.domain.models import TimeSignature

# Absolute note-value grids (whole-note units). Using absolute 1/8 and 1/16
# rather than beat-relative subdivisions keeps every onset on a 1/16 grid, which
# makes the notation render with standard durations in ANY meter (incl.
# compound), and gives musically-correct eighth-note hi-hats regardless of meter.
_EIGHTH = Fraction(1, 8)
_SIXTEENTH = Fraction(1, 16)


class GrooveRequest(BaseModel):
    time_sig: TimeSignature
    num_bars: int = Field(ge=1, le=64)
    tempo_bpm: int = Field(ge=1)
    difficulty: Difficulty = Difficulty.BEGINNER
    seed: int | None = None


def _beats(ts: TimeSignature) -> tuple[Fraction, int]:
    beat = ts.beat_length
    return beat, int(ts.bar_length / beat)


def _hihat(ts: TimeSignature, difficulty: Difficulty, rng: random.Random) -> list[Hit]:
    beat, _ = _beats(ts)
    eighth = _EIGHTH
    sixteenth = _SIXTEENTH
    bar = ts.bar_length

    # Base eighth-note grid on the right hand.
    onsets: list[Fraction] = []
    o = Fraction(0)
    while o < bar:
        onsets.append(o)
        o += eighth

    # Advanced: sprinkle 16th insertions between some eighths.
    if difficulty is Difficulty.PRO:
        extra = [o + sixteenth for o in onsets if o + sixteenth < bar and rng.random() < 0.3]
        onsets = sorted(set(onsets) | set(extra))

    # An open hi-hat accent: the last eighth of the bar (mid sometimes, pro often).
    open_onset: Fraction | None = None
    last_eighth = bar - eighth
    if (difficulty is Difficulty.MID and rng.random() < 0.5) or (
        difficulty is Difficulty.PRO and rng.random() < 0.8
    ):
        open_onset = last_eighth

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

    # Mid/Pro: a couple of ghost notes on off-beat eighths (never on a backbeat).
    if difficulty is not Difficulty.BEGINNER:
        taken = {h.onset for h in hits}
        candidates = [
            b * beat + eighth for b in range(num_beats) if b * beat + eighth < ts.bar_length
        ]
        rng.shuffle(candidates)
        for on in candidates[: (2 if difficulty is Difficulty.PRO else 1)]:
            if on not in taken:
                hits.append(
                    Hit(
                        onset=on,
                        duration=eighth,
                        surface=Surface.SNARE,
                        hand=Hand.L,
                        ghost=True,
                    )
                )
    return hits


def _kick(ts: TimeSignature, difficulty: Difficulty, rng: random.Random) -> list[Hit]:
    beat, num_beats = _beats(ts)
    eighth = _EIGHTH
    sixteenth = _SIXTEENTH
    bar = ts.bar_length

    # Beginner foundation: beat 1 and the mid-bar beat.
    onsets: list[Fraction] = [Fraction(0)]
    mid = num_beats // 2
    if mid > 0:
        onsets.append(mid * beat)

    hits: list[Hit] = []
    if difficulty is Difficulty.BEGINNER:
        for on in onsets:
            hits.append(Hit(onset=on, duration=eighth, surface=Surface.KICK))
        return hits

    if difficulty is Difficulty.MID:
        # Add 1-2 syncopated "and of the beat" kicks.
        ands = [b * beat + eighth for b in range(num_beats) if b * beat + eighth < bar]
        rng.shuffle(ands)
        onsets = sorted(set(onsets) | set(ands[:2]))
        for on in onsets:
            hits.append(Hit(onset=on, duration=eighth, surface=Surface.KICK))
        return hits

    # Pro: double-pedal (kardan) - base kicks plus a 16th foot-run on the last
    # beat, alternating feet (R/L).
    for on in onsets:
        hits.append(Hit(onset=on, duration=sixteenth, surface=Surface.KICK, hand=Hand.R))
    run_start = (num_beats - 1) * beat
    foot = Hand.R
    o = run_start
    while o < bar:
        if all(h.onset != o for h in hits):
            hits.append(Hit(onset=o, duration=sixteenth, surface=Surface.KICK, hand=foot))
        foot = foot.other()
        o += sixteenth
    return hits


def _finest_subdivision(_ts: TimeSignature, difficulty: Difficulty) -> Fraction:
    return _SIXTEENTH if difficulty is Difficulty.PRO else _EIGHTH


def generate_groove(req: GrooveRequest) -> Groove:
    rng = random.Random(req.seed)
    bars = [
        GrooveBar(
            time_sig=req.time_sig,
            hands=[
                *_hihat(req.time_sig, req.difficulty, rng),
                *_snare(req.time_sig, req.difficulty, rng),
            ],
            feet=_kick(req.time_sig, req.difficulty, rng),
        )
        for _ in range(req.num_bars)
    ]
    subdivision: FractionField = _finest_subdivision(req.time_sig, req.difficulty)
    return Groove(
        time_sig=req.time_sig,
        tempo_bpm=req.tempo_bpm,
        subdivision=subdivision,
        bars=bars,
    )
