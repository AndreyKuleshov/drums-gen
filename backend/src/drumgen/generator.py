import random
from fractions import Fraction

from pydantic import BaseModel, Field

from drumgen.catalog import MVP_CATALOG, RudimentTemplate
from drumgen.domain.enums import AccentMode, Articulation, Difficulty
from drumgen.domain.fractions import FractionField
from drumgen.domain.models import Bar, Phrase, Stroke, TimeSignature
from drumgen.rules import find_violations

_DIFFICULTY_ORDER: dict[Difficulty, int] = {
    Difficulty.BEGINNER: 0,
    Difficulty.MID: 1,
    Difficulty.PRO: 2,
}
_GRACE_ARTICULATION: dict[int, Articulation] = {
    1: Articulation.FLAM,
    2: Articulation.DRAG,
}


class GenerationError(Exception):
    pass


class GenerateRequest(BaseModel):
    time_sig: TimeSignature
    num_bars: int = Field(ge=1, le=64)
    min_subdivision: FractionField
    tempo_bpm: int = Field(ge=1)
    accent_mode: AccentMode
    seed: int | None = None
    mixed: bool = False
    """When true, rudiments are placed at varied note values (mix of e.g. quarters,
    eighths, sixteenths) instead of a single uniform subdivision."""
    authentic: bool = False
    """When true, rudiments carry their internal rhythm (per-element durations),
    e.g. a roll's diddles are short and its accented release is longer."""
    difficulty: Difficulty = Difficulty.MID
    """Selects which rudiments may be used: beginner = simple strokes/paradiddle,
    mid = + longer paradiddles and rolls, pro = + flams and drags."""


def _is_metric_strong(pos: Fraction, beat: Fraction) -> bool:
    """True when a stroke starting at `pos` (from bar start) lands on a beat."""
    return (pos / beat).denominator == 1


def _resolve_accent(template_accent: bool, is_strong: bool, mode: AccentMode) -> bool:
    if mode is AccentMode.RUDIMENT:
        return template_accent
    if mode is AccentMode.METRIC:
        return is_strong
    return template_accent or is_strong


# Atomic elements used only as fillers when no real rudiment fits the remaining
# space; keeping them out of the primary pool stops patterns from collapsing into
# nothing but single/double strokes.
_FILLER_IDS = frozenset({"single", "double"})


def _orientations(templates: list[RudimentTemplate]) -> list[RudimentTemplate]:
    """Each template plus its L/R mirror."""
    out: list[RudimentTemplate] = []
    for t in templates:
        out.append(t)
        out.append(t.mirrored())
    return out


def _note_values(subdivision: Fraction, bar_length: Fraction, mixed: bool) -> list[Fraction]:
    """Allowed per-stroke note values.

    Uniform mode: just the base subdivision. Mixed mode: the base plus its
    power-of-two multiples up to a quarter note (or the bar), so a bar can hold
    e.g. quarters, eighths and sixteenths together. All values are multiples of
    the base, so any partial fill stays an exact multiple and the bar can always
    be completed with base-value filler strokes.
    """
    if not mixed:
        return [subdivision]
    cap = min(Fraction(1, 4), bar_length)
    values: list[Fraction] = []
    value = subdivision
    while value <= cap:
        values.append(value)
        value *= 2
    return values or [subdivision]


def generate(req: GenerateRequest) -> Phrase:
    subdivision = req.min_subdivision
    if subdivision <= 0:
        msg = f"min_subdivision must be positive, got {subdivision}"
        raise GenerationError(msg)
    bar_length = req.time_sig.bar_length
    cells_ratio = bar_length / subdivision
    if cells_ratio.denominator != 1 or cells_ratio.numerator < 1:
        msg = f"bar {bar_length} not divisible by subdivision {subdivision}"
        raise GenerationError(msg)

    total_cells = cells_ratio.numerator * req.num_bars
    max_cells = 1024
    if total_cells > max_cells:
        msg = f"pattern too large: {total_cells} cells exceeds limit {max_cells}"
        raise GenerationError(msg)

    beat = req.time_sig.beat_length
    values = _note_values(subdivision, bar_length, req.mixed)
    rng = random.Random(req.seed)
    # Allowed rudiments: this difficulty tier and everything easier.
    max_tier = _DIFFICULTY_ORDER[req.difficulty]
    allowed = [t for t in MVP_CATALOG if _DIFFICULTY_ORDER[t.difficulty] <= max_tier]
    phrase_pool = _orientations([t for t in allowed if t.id not in _FILLER_IDS])
    filler_pool = _orientations([t for t in allowed if t.id in _FILLER_IDS])

    def build(template: RudimentTemplate, value: Fraction, start: Fraction) -> list[Stroke]:
        strokes: list[Stroke] = []
        offset = Fraction(0)
        for elem in template.elements:
            weight = elem.weight if req.authentic else 1
            pos = start + offset
            is_strong = _is_metric_strong(pos, beat)
            strokes.append(
                Stroke(
                    duration=weight * value,
                    hand=elem.hand,
                    accent=_resolve_accent(elem.accent, is_strong, req.accent_mode),
                    grace=elem.grace,
                    articulation=_GRACE_ARTICULATION.get(elem.grace, Articulation.NORMAL),
                )
            )
            offset += weight * value
        return strokes

    def span_units(template: RudimentTemplate) -> int:
        return template.total_weight if req.authentic else template.length_cells

    # Fill unit: the whole bar (uniform) or a single beat (mixed, so each beat can
    # take a different note value). Each unit is filled with rudiments at one value.
    unit = beat if req.mixed else bar_length
    units_per_bar = int(bar_length / unit)

    def feasible_values(unit_len: Fraction) -> list[Fraction]:
        vals = [v for v in values if (unit_len / v).denominator == 1]
        return vals or [subdivision]

    def solve(
        bar_index: int,
        unit_index: int,
        pos_in_unit: Fraction,
        value: Fraction | None,
        flat: list[Stroke],
        segments: list[list[Stroke]],
    ) -> list[list[Stroke]] | None:
        if bar_index == req.num_bars:
            # The phrase is meant to loop, so the wrap-around seam (last strokes
            # -> first strokes) must also obey the rules.
            if len(flat) >= 2 and find_violations(flat[-2:] + flat[:2]):
                return None
            return segments
        if pos_in_unit == unit:
            next_unit = unit_index + 1
            if next_unit == units_per_bar:
                return solve(bar_index + 1, 0, Fraction(0), None, flat, segments)
            return solve(bar_index, next_unit, Fraction(0), None, flat, segments)
        if value is None:
            candidates = feasible_values(unit)
            candidates = candidates[:]
            rng.shuffle(candidates)
            for chosen in candidates:
                result = solve(bar_index, unit_index, pos_in_unit, chosen, flat, segments)
                if result is not None:
                    return result
            return None

        remaining = unit - pos_in_unit
        start = unit_index * unit + pos_in_unit
        phrase_shuffled = phrase_pool[:]
        rng.shuffle(phrase_shuffled)
        filler_shuffled = filler_pool[:]
        rng.shuffle(filler_shuffled)
        for template in (*phrase_shuffled, *filler_shuffled):
            span = span_units(template) * value
            if span > remaining:
                continue
            new_strokes = build(template, value, start)
            if find_violations(flat[-2:] + new_strokes):
                continue
            result = solve(
                bar_index,
                unit_index,
                pos_in_unit + span,
                value,
                [*flat, *new_strokes],
                [*segments, new_strokes],
            )
            if result is not None:
                return result
        return None

    segments = solve(0, 0, Fraction(0), None, [], [])
    if segments is None:
        msg = "no valid tiling found for the given parameters"
        raise GenerationError(msg)

    # Tag strokes with their rudiment-instance index (for beaming) and split the
    # placement segments back into bars by accumulating durations.
    bar_strokes: list[list[Stroke]] = [[]]
    filled = Fraction(0)
    for group_index, segment in enumerate(segments):
        for stroke in segment:
            bar_strokes[-1].append(stroke.model_copy(update={"group": group_index}))
        filled += sum((s.duration for s in segment), Fraction(0))
        if filled == bar_length:
            filled = Fraction(0)
            bar_strokes.append([])
    if not bar_strokes[-1]:
        bar_strokes.pop()

    bars = [Bar(time_sig=req.time_sig, strokes=strokes) for strokes in bar_strokes]
    return Phrase(
        time_sig=req.time_sig,
        tempo_bpm=req.tempo_bpm,
        subdivision=subdivision,
        accent_mode=req.accent_mode,
        bars=bars,
    )
