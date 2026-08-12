"""Polyphonic kit-groove model (Pattern mode).

Unlike the monophonic rudiment `Phrase` (a sequence of single strokes summing
to the bar), a groove has voices that sound simultaneously: hi-hat + snare are
played by the HANDS, the kick by the FEET. Each bar therefore holds two voices,
each an onset-keyed list of hits (with gaps, unlike the rudiment path).
"""

from fractions import Fraction

from pydantic import BaseModel, model_validator

from drumgen.domain.enums import Articulation, Hand, Surface
from drumgen.domain.fractions import FractionField
from drumgen.domain.models import TimeSignature


class Hit(BaseModel):
    onset: FractionField
    """Start position within the bar, in whole-note units (0 = downbeat)."""
    duration: FractionField
    surface: Surface
    hand: Hand | None = None
    """Which hand plays it (hi-hat/snare). None for the kick (feet)."""
    accent: bool = False
    ghost: bool = False
    articulation: Articulation = Articulation.NORMAL


class GrooveBar(BaseModel):
    time_sig: TimeSignature
    hands: list[Hit]
    """Hi-hat + snare, notated as the stems-up voice."""
    feet: list[Hit]
    """Kick, notated as the stems-down voice."""

    @model_validator(mode="after")
    def _check(self) -> "GrooveBar":
        length = self.time_sig.bar_length
        for hit in [*self.hands, *self.feet]:
            if not (0 <= hit.onset < length):
                msg = f"onset {hit.onset} out of bar [0, {length})"
                raise ValueError(msg)
        # Hand exclusivity: a hand can't be on hi-hat AND snare at the same onset.
        booked: dict[Fraction, set[Hand]] = {}
        for hit in self.hands:
            if hit.hand is None:
                continue
            if hit.hand in booked.get(hit.onset, set()):
                msg = f"hand {hit.hand} double-booked at onset {hit.onset}"
                raise ValueError(msg)
            booked.setdefault(hit.onset, set()).add(hit.hand)
        return self


class Groove(BaseModel):
    time_sig: TimeSignature
    tempo_bpm: int
    subdivision: FractionField
    bars: list[GrooveBar]
