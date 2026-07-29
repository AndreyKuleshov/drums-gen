import random
from fractions import Fraction

from pydantic import BaseModel, Field

from drumgen.catalog import MVP_CATALOG, RudimentTemplate
from drumgen.domain.enums import AccentMode
from drumgen.domain.fractions import FractionField
from drumgen.domain.models import Bar, Phrase, Stroke, TimeSignature
from drumgen.rules import find_violations


class GenerationError(Exception):
    pass


class GenerateRequest(BaseModel):
    time_sig: TimeSignature
    num_bars: int = Field(ge=1, le=64)
    min_subdivision: FractionField
    tempo_bpm: int = Field(ge=1)
    accent_mode: AccentMode
    seed: int | None = None


def _metric_strong_cells(time_sig: TimeSignature, subdivision: Fraction) -> set[int]:
    beat = time_sig.beat_length
    cells_per_bar = time_sig.bar_length / subdivision
    n = cells_per_bar.numerator
    strong: set[int] = set()
    for i in range(n):
        if ((subdivision * i) / beat).denominator == 1:
            strong.add(i)
    return strong


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


def generate(req: GenerateRequest) -> Phrase:
    subdivision = req.min_subdivision
    if subdivision <= 0:
        msg = f"min_subdivision must be positive, got {subdivision}"
        raise GenerationError(msg)
    cells_ratio = req.time_sig.bar_length / subdivision
    if cells_ratio.denominator != 1 or cells_ratio.numerator < 1:
        msg = f"bar {req.time_sig.bar_length} not divisible by subdivision {subdivision}"
        raise GenerationError(msg)
    if req.num_bars < 1:
        msg = "num_bars must be >= 1"
        raise GenerationError(msg)

    cells_per_bar = cells_ratio.numerator
    total_cells = cells_per_bar * req.num_bars
    max_cells = 1024
    if total_cells > max_cells:
        msg = f"pattern too large: {total_cells} cells exceeds limit {max_cells}"
        raise GenerationError(msg)
    strong = _metric_strong_cells(req.time_sig, subdivision)
    rng = random.Random(req.seed)
    phrase_pool = _orientations([t for t in MVP_CATALOG if t.id not in _FILLER_IDS])
    filler_pool = _orientations([t for t in MVP_CATALOG if t.id in _FILLER_IDS])

    def build(template: RudimentTemplate, pos: int) -> list[Stroke]:
        strokes: list[Stroke] = []
        for k, elem in enumerate(template.elements):
            is_strong = (pos + k) % cells_per_bar in strong
            strokes.append(
                Stroke(
                    duration=subdivision,
                    hand=elem.hand,
                    accent=_resolve_accent(elem.accent, is_strong, req.accent_mode),
                )
            )
        return strokes

    def solve(
        pos: int, flat: list[Stroke], segments: list[list[Stroke]]
    ) -> list[list[Stroke]] | None:
        if pos == total_cells:
            return segments
        remaining_in_bar = cells_per_bar - (pos % cells_per_bar)
        # Try real rudiments first (shuffled per position for variety), falling
        # back to single/double fillers only when nothing else fits.
        phrase_shuffled = phrase_pool[:]
        rng.shuffle(phrase_shuffled)
        filler_shuffled = filler_pool[:]
        rng.shuffle(filler_shuffled)
        for template in (*phrase_shuffled, *filler_shuffled):
            if template.length_cells > remaining_in_bar:
                continue
            new_strokes = build(template, pos)
            if find_violations(flat[-2:] + new_strokes):
                continue
            result = solve(
                pos + template.length_cells,
                [*flat, *new_strokes],
                [*segments, new_strokes],
            )
            if result is not None:
                return result
        return None

    segments = solve(0, [], [])
    if segments is None:
        msg = "no valid tiling found for the given parameters"
        raise GenerationError(msg)

    # Tag each stroke with its rudiment-instance index so the frontend can beam
    # notes together by rudiment phrase.
    flat = [
        stroke.model_copy(update={"group": group_index})
        for group_index, segment in enumerate(segments)
        for stroke in segment
    ]

    bars = [
        Bar(
            time_sig=req.time_sig,
            strokes=flat[i * cells_per_bar : (i + 1) * cells_per_bar],
        )
        for i in range(req.num_bars)
    ]
    return Phrase(
        time_sig=req.time_sig,
        tempo_bpm=req.tempo_bpm,
        subdivision=subdivision,
        accent_mode=req.accent_mode,
        bars=bars,
    )
