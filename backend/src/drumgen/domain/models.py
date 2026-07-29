from fractions import Fraction

from pydantic import BaseModel, model_validator

from drumgen.domain.enums import AccentMode, Articulation, Hand, Surface
from drumgen.domain.fractions import FractionField


class TimeSignature(BaseModel):
    num: int
    den: int

    @property
    def bar_length(self) -> Fraction:
        return Fraction(self.num, self.den)

    def is_compound(self) -> bool:
        return self.den in (8, 16) and self.num % 3 == 0 and self.num > 3

    @property
    def beat_length(self) -> Fraction:
        if self.is_compound():
            return Fraction(3, self.den)
        return Fraction(1, self.den)


class Stroke(BaseModel):
    duration: FractionField
    hand: Hand
    accent: bool = False
    articulation: Articulation = Articulation.NORMAL
    surface: Surface = Surface.SNARE


class Bar(BaseModel):
    time_sig: TimeSignature
    strokes: list[Stroke]

    @model_validator(mode="after")
    def _check_bar_length(self) -> "Bar":
        total = sum((s.duration for s in self.strokes), Fraction(0))
        if total != self.time_sig.bar_length:
            msg = f"bar length {total} != expected {self.time_sig.bar_length}"
            raise ValueError(msg)
        return self


class Phrase(BaseModel):
    time_sig: TimeSignature
    tempo_bpm: int
    subdivision: FractionField
    accent_mode: AccentMode
    bars: list[Bar]
