# Drum Pattern Generator MVP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deterministic web platform that generates valid snare-drum rudiment patterns of a given meter/length, renders them as notation, and plays them back cross-platform.

**Architecture:** Python backend (Pydantic domain models + backtracking generator + rule validator + FastAPI). Vue 3 frontend renders the returned `Phrase` JSON via VexFlow and schedules playback via Tone.js. Monorepo: `backend/` + `frontend/`.

**Tech Stack:** Python 3.12, uv, Pydantic v2, FastAPI, pytest, Hypothesis, ruff (strict), pyright (strict). Vue 3 + Vite + TypeScript, VexFlow, Tone.js, Vitest.

## Global Constraints

- Python 3.12+; all backend code fully type-annotated; `pyright` strict must pass with zero errors.
- `ruff check` and `ruff format --check` must pass (strict rule set defined in Task 1).
- Backend uses **src layout**; import package name is `drumgen`.
- Durations are `fractions.Fraction`, never `float`. JSON representation of a duration is the string `"num/den"` (e.g. `"1/12"`).
- **MVP uniform-grid constraint:** every stroke of every rudiment occupies exactly one `min_subdivision` cell (all strokes in a phrase share one duration = `min_subdivision`). Mixed-duration rudiments, flams, drags, grace notes, and buzz are phase 2 — out of scope here.
- Sticking rules are checked on **main notes only** (MVP has no grace notes, so all strokes are main).
- Two hard rules (see spec §5): (R1) no accented stroke immediately after an unaccented stroke of the same hand; (R2) no three consecutive strokes of the same hand.
- Frontend: Node 20+, Vue 3 `<script setup>`, TypeScript `strict: true`, `vue-tsc` must pass.
- Every task ends on a green test run and a commit.

## File Structure

```
backend/
  pyproject.toml
  pyrightconfig.json
  src/drumgen/__init__.py
  src/drumgen/domain/__init__.py
  src/drumgen/domain/fractions.py   # FractionField (Annotated Fraction <-> "n/d")
  src/drumgen/domain/enums.py       # Hand, Articulation, Surface, AccentMode
  src/drumgen/domain/models.py      # TimeSignature, Stroke, Bar, Phrase
  src/drumgen/rules.py              # find_violations, RuleViolation
  src/drumgen/catalog.py            # RudimentElement, RudimentTemplate, MVP_CATALOG
  src/drumgen/generator.py          # generate(), GenerationError, GenerateRequest
  src/drumgen/api.py                # FastAPI app
  tests/
    test_fractions.py
    test_models.py
    test_rules.py
    test_catalog.py
    test_generator.py
    test_api.py
frontend/
  package.json
  tsconfig.json
  vite.config.ts
  index.html
  src/main.ts
  src/App.vue
  src/types.ts                      # Phrase JSON types
  src/lib/score.ts                  # Phrase -> VexFlow primitives (pure)
  src/lib/audio.ts                  # schedule (pure) + Tone.js player
  src/components/GenerationForm.vue
  src/components/ScoreView.vue
  src/components/PlayerControls.vue
  src/lib/__tests__/score.test.ts
  src/lib/__tests__/audio.test.ts
```

---

## Task 1: Backend scaffold (uv, ruff strict, pyright strict, pytest)

**Files:**
- Create: `backend/pyproject.toml`
- Create: `backend/pyrightconfig.json`
- Create: `backend/src/drumgen/__init__.py`
- Create: `backend/src/drumgen/domain/__init__.py`
- Create: `backend/tests/test_smoke.py`

**Interfaces:**
- Produces: importable package `drumgen`; working `uv run` / `uv run pytest` / `uv run ruff` / `uv run pyright`.

- [ ] **Step 1: Create `backend/pyproject.toml`**

```toml
[project]
name = "drumgen"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "pydantic>=2.6",
    "fastapi>=0.110",
    "uvicorn>=0.29",
]

[dependency-groups]
dev = [
    "pytest>=8.0",
    "hypothesis>=6.100",
    "httpx>=0.27",
    "ruff>=0.5",
    "pyright>=1.1.360",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/drumgen"]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "N", "UP", "B", "A", "C4", "SIM", "RUF", "ANN", "PT"]
ignore = ["ANN401"]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["ANN201", "ANN001"]
```

- [ ] **Step 2: Create `backend/pyrightconfig.json`**

```json
{
  "include": ["src", "tests"],
  "extraPaths": ["src"],
  "typeCheckingMode": "strict",
  "pythonVersion": "3.12",
  "reportMissingTypeStubs": false
}
```

- [ ] **Step 3: Create empty package files**

`backend/src/drumgen/__init__.py`:
```python
```
`backend/src/drumgen/domain/__init__.py`:
```python
```

- [ ] **Step 4: Write smoke test `backend/tests/test_smoke.py`**

```python
import drumgen


def test_package_importable():
    assert drumgen is not None
```

- [ ] **Step 5: Sync and run the toolchain**

Run:
```bash
cd backend && uv sync && uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run pyright
```
Expected: `uv sync` installs deps; pytest reports `1 passed`; ruff check passes; ruff format check passes; pyright reports `0 errors`.

- [ ] **Step 6: Commit**

```bash
git add backend/pyproject.toml backend/pyrightconfig.json backend/src backend/tests backend/uv.lock
git commit -m "chore(backend): scaffold uv + ruff strict + pyright strict + pytest"
```

---

## Task 2: FractionField (Pydantic <-> "n/d")

**Files:**
- Create: `backend/src/drumgen/domain/fractions.py`
- Test: `backend/tests/test_fractions.py`

**Interfaces:**
- Produces: `FractionField` — an `Annotated[Fraction, ...]` type alias usable as a Pydantic field. Validates from `Fraction | str | int`; serializes to `"num/den"`; JSON schema is `{"type": "string"}`.

- [ ] **Step 1: Write the failing test `backend/tests/test_fractions.py`**

```python
from fractions import Fraction

from pydantic import BaseModel

from drumgen.domain.fractions import FractionField


class _M(BaseModel):
    d: FractionField


def test_parse_from_string():
    assert _M(d="1/12").d == Fraction(1, 12)


def test_parse_from_fraction():
    assert _M(d=Fraction(3, 8)).d == Fraction(3, 8)


def test_parse_from_int():
    assert _M(d=1).d == Fraction(1, 1)


def test_serialize_to_string():
    assert _M(d=Fraction(1, 12)).model_dump(mode="json") == {"d": "1/12"}


def test_json_schema_is_string():
    assert _M.model_json_schema()["properties"]["d"]["type"] == "string"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_fractions.py -q`
Expected: FAIL — `ModuleNotFoundError: drumgen.domain.fractions`.

- [ ] **Step 3: Implement `backend/src/drumgen/domain/fractions.py`**

```python
from fractions import Fraction
from typing import Annotated

from pydantic import PlainSerializer, PlainValidator, WithJsonSchema


def _parse_fraction(value: object) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, str):
        return Fraction(value)
    msg = f"cannot parse Fraction from {value!r}"
    raise TypeError(msg)


def _serialize_fraction(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


FractionField = Annotated[
    Fraction,
    PlainValidator(_parse_fraction),
    PlainSerializer(_serialize_fraction, return_type=str),
    WithJsonSchema({"type": "string", "pattern": r"^-?\d+/\d+$", "examples": ["1/12"]}),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_fractions.py -q && uv run pyright`
Expected: all pass; pyright `0 errors`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/drumgen/domain/fractions.py backend/tests/test_fractions.py
git commit -m "feat(domain): FractionField pydantic type serializing to n/d"
```

---

## Task 3: Enums

**Files:**
- Create: `backend/src/drumgen/domain/enums.py`
- Test: `backend/tests/test_models.py` (created here, extended later)

**Interfaces:**
- Produces: `Hand` (`L`,`R` values `"L"`,`"R"`), `Articulation` (`NORMAL`,`FLAM`,`DRAG`,`BUZZ`), `Surface` (`SNARE`), `AccentMode` (`RUDIMENT`,`METRIC`,`BOTH`). All are `str, Enum`.

- [ ] **Step 1: Write the failing test (append to `backend/tests/test_models.py`)**

```python
from drumgen.domain.enums import AccentMode, Articulation, Hand, Surface


def test_enum_values():
    assert Hand.R.value == "R"
    assert Hand.L.value == "L"
    assert Articulation.NORMAL.value == "normal"
    assert Surface.SNARE.value == "snare"
    assert {m.value for m in AccentMode} == {"rudiment", "metric", "both"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_models.py -q`
Expected: FAIL — `ModuleNotFoundError: drumgen.domain.enums`.

- [ ] **Step 3: Implement `backend/src/drumgen/domain/enums.py`**

```python
from enum import Enum


class Hand(str, Enum):
    L = "L"
    R = "R"

    def other(self) -> "Hand":
        return Hand.L if self is Hand.R else Hand.R


class Articulation(str, Enum):
    NORMAL = "normal"
    FLAM = "flam"
    DRAG = "drag"
    BUZZ = "buzz"


class Surface(str, Enum):
    SNARE = "snare"


class AccentMode(str, Enum):
    RUDIMENT = "rudiment"
    METRIC = "metric"
    BOTH = "both"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_models.py -q && uv run pyright`
Expected: pass; pyright `0 errors`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/drumgen/domain/enums.py backend/tests/test_models.py
git commit -m "feat(domain): Hand/Articulation/Surface/AccentMode enums"
```

---

## Task 4: Domain models — TimeSignature, Stroke, Bar, Phrase

**Files:**
- Create: `backend/src/drumgen/domain/models.py`
- Test: `backend/tests/test_models.py` (extend)

**Interfaces:**
- Consumes: `FractionField` (Task 2); enums (Task 3).
- Produces:
  - `TimeSignature(num: int, den: int)` with `.bar_length -> Fraction` (`Fraction(num, den)`), `.beat_length -> Fraction`, `.is_compound() -> bool`.
  - `Stroke(duration: FractionField, hand: Hand, accent: bool = False, articulation: Articulation = NORMAL, surface: Surface = SNARE)`.
  - `Bar(time_sig: TimeSignature, strokes: list[Stroke])` — `model_validator(mode="after")` raises `ValueError` if `sum(durations) != time_sig.bar_length`.
  - `Phrase(time_sig, tempo_bpm: int, subdivision: FractionField, accent_mode: AccentMode, bars: list[Bar])`.

- [ ] **Step 1: Write the failing tests (append to `backend/tests/test_models.py`)**

```python
from fractions import Fraction

import pytest
from pydantic import ValidationError

from drumgen.domain.models import Bar, Phrase, Stroke, TimeSignature


def test_bar_length_and_beat():
    assert TimeSignature(num=4, den=4).bar_length == Fraction(4, 4)
    assert TimeSignature(num=4, den=4).beat_length == Fraction(1, 4)
    assert TimeSignature(num=6, den=8).is_compound() is True
    assert TimeSignature(num=6, den=8).beat_length == Fraction(3, 8)
    assert TimeSignature(num=3, den=4).is_compound() is False


def test_bar_invariant_accepts_exact_fill():
    ts = TimeSignature(num=2, den=4)
    strokes = [Stroke(duration=Fraction(1, 4), hand="R") for _ in range(2)]
    bar = Bar(time_sig=ts, strokes=strokes)
    assert len(bar.strokes) == 2


def test_bar_invariant_rejects_wrong_sum():
    ts = TimeSignature(num=2, den=4)
    with pytest.raises(ValidationError):
        Bar(time_sig=ts, strokes=[Stroke(duration=Fraction(1, 4), hand="R")])


def test_phrase_roundtrips_json():
    ts = TimeSignature(num=1, den=4)
    phrase = Phrase(
        time_sig=ts,
        tempo_bpm=100,
        subdivision=Fraction(1, 4),
        accent_mode="rudiment",
        bars=[Bar(time_sig=ts, strokes=[Stroke(duration=Fraction(1, 4), hand="L")])],
    )
    dumped = phrase.model_dump(mode="json")
    assert dumped["bars"][0]["strokes"][0]["duration"] == "1/4"
    assert Phrase.model_validate(dumped).tempo_bpm == 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_models.py -q`
Expected: FAIL — `ModuleNotFoundError: drumgen.domain.models`.

- [ ] **Step 3: Implement `backend/src/drumgen/domain/models.py`**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_models.py -q && uv run pyright && uv run ruff check .`
Expected: all pass; pyright `0 errors`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/drumgen/domain/models.py backend/tests/test_models.py
git commit -m "feat(domain): TimeSignature/Stroke/Bar/Phrase with bar-length invariant"
```

---

## Task 5: Sticking-rule validator

**Files:**
- Create: `backend/src/drumgen/rules.py`
- Test: `backend/tests/test_rules.py`

**Interfaces:**
- Consumes: `Stroke`, `Hand` (Task 4/3).
- Produces:
  - `RuleViolation(BaseModel)` with `index: int`, `rule: str` (`"R1"` or `"R2"`), `message: str`.
  - `find_violations(strokes: Sequence[Stroke]) -> list[RuleViolation]`.
  - `is_valid(strokes: Sequence[Stroke]) -> bool`.

- [ ] **Step 1: Write the failing tests `backend/tests/test_rules.py`**

```python
from fractions import Fraction

from drumgen.domain.models import Stroke
from drumgen.rules import find_violations, is_valid


def _s(hand: str, accent: bool = False) -> Stroke:
    return Stroke(duration=Fraction(1, 16), hand=hand, accent=accent)


def test_clean_sequence_has_no_violations():
    strokes = [_s("R"), _s("L"), _s("R"), _s("L")]
    assert find_violations(strokes) == []
    assert is_valid(strokes) is True


def test_rule1_accent_after_unaccent_same_hand():
    # rR: unaccented R then accented R
    strokes = [_s("R", accent=False), _s("R", accent=True)]
    violations = find_violations(strokes)
    assert [v.rule for v in violations] == ["R1"]
    assert violations[0].index == 1


def test_rule1_allows_accent_after_unaccent_different_hand():
    strokes = [_s("R", accent=False), _s("L", accent=True)]
    assert find_violations(strokes) == []


def test_rule2_three_same_hand_in_a_row():
    strokes = [_s("R"), _s("R"), _s("R")]
    violations = find_violations(strokes)
    assert [v.rule for v in violations] == ["R2"]
    assert violations[0].index == 2


def test_two_same_hand_is_allowed():
    strokes = [_s("R"), _s("R"), _s("L")]
    assert find_violations(strokes) == []
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_rules.py -q`
Expected: FAIL — `ModuleNotFoundError: drumgen.rules`.

- [ ] **Step 3: Implement `backend/src/drumgen/rules.py`**

```python
from collections.abc import Sequence

from pydantic import BaseModel

from drumgen.domain.models import Stroke


class RuleViolation(BaseModel):
    index: int
    rule: str
    message: str


def find_violations(strokes: Sequence[Stroke]) -> list[RuleViolation]:
    violations: list[RuleViolation] = []
    for i in range(1, len(strokes)):
        prev, cur = strokes[i - 1], strokes[i]
        if cur.hand == prev.hand and not prev.accent and cur.accent:
            violations.append(
                RuleViolation(
                    index=i,
                    rule="R1",
                    message=f"accented {cur.hand.value} after unaccented {prev.hand.value}",
                )
            )
    for i in range(2, len(strokes)):
        if strokes[i].hand == strokes[i - 1].hand == strokes[i - 2].hand:
            violations.append(
                RuleViolation(
                    index=i,
                    rule="R2",
                    message=f"three {strokes[i].hand.value} strokes in a row",
                )
            )
    return sorted(violations, key=lambda v: (v.index, v.rule))


def is_valid(strokes: Sequence[Stroke]) -> bool:
    return not find_violations(strokes)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_rules.py -q && uv run pyright`
Expected: pass; pyright `0 errors`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/drumgen/rules.py backend/tests/test_rules.py
git commit -m "feat(rules): R1/R2 sticking-rule validator on main notes"
```

---

## Task 6: Rudiment catalog

**Files:**
- Create: `backend/src/drumgen/catalog.py`
- Test: `backend/tests/test_catalog.py`

**Interfaces:**
- Consumes: `Hand`, `Stroke`, `find_violations` (Tasks 3/4/5).
- Produces:
  - `RudimentElement(BaseModel)` with `hand: Hand`, `accent: bool`.
  - `RudimentTemplate(BaseModel)` with `id: str`, `name: str`, `elements: list[RudimentElement]`, `mvp: bool`, `violates_core_rules: bool`; property `length_cells -> int`; method `mirrored() -> RudimentTemplate` (swaps every hand, keeps accents, id suffixed `"-mirror"`).
  - `MVP_CATALOG: list[RudimentTemplate]` — only `mvp=True, violates_core_rules=False` templates: `single`, `double`, `single-paradiddle`, `double-paradiddle`, `triple-paradiddle`, `paradiddle-diddle`, `five-stroke-roll`, `seven-stroke-roll`.
  - `FULL_CATALOG: list[RudimentTemplate]` — `MVP_CATALOG` plus at least one flagged template `triple-stroke` (`violates_core_rules=True`, `mvp=False`).

Sticking definitions (accent on first stroke unless noted; rolls accent the final tap):
- single: `R` (1 cell)
- double: `R R` (2 cells)
- single-paradiddle: `R L R R` (4 cells, accent first)
- double-paradiddle: `R L R L R R` (6 cells, accent first)
- triple-paradiddle: `R L R L R L R R` (8 cells, accent first)
- paradiddle-diddle: `R L R R L L` (6 cells, accent first)
- five-stroke-roll: `R R L L R` (5 cells, accent last)
- seven-stroke-roll: `R R L L R R L` (7 cells, accent last)
- triple-stroke (flagged): `R R R` (3 cells) — violates R2

- [ ] **Step 1: Write the failing tests `backend/tests/test_catalog.py`**

```python
from fractions import Fraction

from drumgen.catalog import FULL_CATALOG, MVP_CATALOG, RudimentTemplate
from drumgen.domain.models import Stroke
from drumgen.rules import find_violations


def _to_strokes(t: RudimentTemplate) -> list[Stroke]:
    return [
        Stroke(duration=Fraction(1, 16), hand=e.hand, accent=e.accent) for e in t.elements
    ]


def test_mvp_catalog_not_empty_and_all_valid_flags():
    assert MVP_CATALOG
    for t in MVP_CATALOG:
        assert t.mvp is True
        assert t.violates_core_rules is False


def test_every_mvp_template_internally_passes_rules():
    for t in MVP_CATALOG:
        assert find_violations(_to_strokes(t)) == [], t.id


def test_flagged_template_excluded_from_mvp():
    triple = next(t for t in FULL_CATALOG if t.id == "triple-stroke")
    assert triple.violates_core_rules is True
    assert triple not in MVP_CATALOG
    assert find_violations(_to_strokes(triple)) != []


def test_mirrored_swaps_hands_keeps_accents():
    single_pd = next(t for t in MVP_CATALOG if t.id == "single-paradiddle")
    m = single_pd.mirrored()
    assert [e.hand.value for e in m.elements] == ["L", "R", "L", "L"]
    assert [e.accent for e in m.elements] == [e.accent for e in single_pd.elements]


def test_length_cells():
    single = next(t for t in MVP_CATALOG if t.id == "single")
    assert single.length_cells == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_catalog.py -q`
Expected: FAIL — `ModuleNotFoundError: drumgen.catalog`.

- [ ] **Step 3: Implement `backend/src/drumgen/catalog.py`**

```python
from pydantic import BaseModel

from drumgen.domain.enums import Hand


class RudimentElement(BaseModel):
    hand: Hand
    accent: bool = False


class RudimentTemplate(BaseModel):
    id: str
    name: str
    elements: list[RudimentElement]
    mvp: bool
    violates_core_rules: bool

    @property
    def length_cells(self) -> int:
        return len(self.elements)

    def mirrored(self) -> "RudimentTemplate":
        return RudimentTemplate(
            id=f"{self.id}-mirror",
            name=f"{self.name} (mirror)",
            elements=[
                RudimentElement(hand=e.hand.other(), accent=e.accent) for e in self.elements
            ],
            mvp=self.mvp,
            violates_core_rules=self.violates_core_rules,
        )


def _elems(sticking: str, accents: set[int]) -> list[RudimentElement]:
    return [
        RudimentElement(hand=Hand(ch), accent=(i in accents))
        for i, ch in enumerate(sticking.replace(" ", ""))
    ]


MVP_CATALOG: list[RudimentTemplate] = [
    RudimentTemplate(
        id="single", name="Single Stroke", elements=_elems("R", set()),
        mvp=True, violates_core_rules=False,
    ),
    RudimentTemplate(
        id="double", name="Double Stroke", elements=_elems("RR", {0}),
        mvp=True, violates_core_rules=False,
    ),
    RudimentTemplate(
        id="single-paradiddle", name="Single Paradiddle", elements=_elems("RLRR", {0}),
        mvp=True, violates_core_rules=False,
    ),
    RudimentTemplate(
        id="double-paradiddle", name="Double Paradiddle", elements=_elems("RLRLRR", {0}),
        mvp=True, violates_core_rules=False,
    ),
    RudimentTemplate(
        id="triple-paradiddle", name="Triple Paradiddle", elements=_elems("RLRLRLRR", {0}),
        mvp=True, violates_core_rules=False,
    ),
    RudimentTemplate(
        id="paradiddle-diddle", name="Paradiddle-diddle", elements=_elems("RLRRLL", {0}),
        mvp=True, violates_core_rules=False,
    ),
    RudimentTemplate(
        id="five-stroke-roll", name="Five Stroke Roll", elements=_elems("RRLLR", {4}),
        mvp=True, violates_core_rules=False,
    ),
    RudimentTemplate(
        id="seven-stroke-roll", name="Seven Stroke Roll", elements=_elems("RRLLRRL", {6}),
        mvp=True, violates_core_rules=False,
    ),
]

FULL_CATALOG: list[RudimentTemplate] = [
    *MVP_CATALOG,
    RudimentTemplate(
        id="triple-stroke", name="Triple Stroke", elements=_elems("RRR", {0}),
        mvp=False, violates_core_rules=True,
    ),
]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_catalog.py -q && uv run pyright && uv run ruff check .`
Expected: pass; pyright `0 errors`. (If `five-stroke-roll`/`seven-stroke-roll` fail R2, they must be corrected — but `RRLLR` and `RRLLRRL` contain no three-in-a-row, so they pass.)

- [ ] **Step 5: Commit**

```bash
git add backend/src/drumgen/catalog.py backend/tests/test_catalog.py
git commit -m "feat(catalog): MVP rudiment templates + flagged triple-stroke"
```

---

## Task 7: Deterministic generator (backtracking, accent modes)

**Files:**
- Create: `backend/src/drumgen/generator.py`
- Test: `backend/tests/test_generator.py`

**Interfaces:**
- Consumes: `TimeSignature`, `Stroke`, `Bar`, `Phrase`, `AccentMode` (Task 4/3); `MVP_CATALOG`, `RudimentTemplate` (Task 6); `find_violations` (Task 5).
- Produces:
  - `GenerationError(Exception)`.
  - `GenerateRequest(BaseModel)`: `time_sig: TimeSignature`, `num_bars: int` (≥1), `min_subdivision: FractionField`, `tempo_bpm: int` (≥1), `accent_mode: AccentMode`, `seed: int | None = None`.
  - `generate(req: GenerateRequest) -> Phrase`. Guarantees: `find_violations` over the concatenated strokes is empty; every `Bar` satisfies its length invariant; each stroke's `duration == min_subdivision`. Raises `GenerationError` if `bar_length / min_subdivision` is not a positive integer, or no valid tiling exists.
  - Helper `_metric_strong_cells(time_sig, subdivision) -> set[int]` and `_resolve_accent(template_accent: bool, is_strong: bool, mode: AccentMode) -> bool` (module-private; tested indirectly).

**Design notes for the implementer:**
- `cells_per_bar = bar_length / min_subdivision` must be an integer; `total_cells = cells_per_bar * num_bars`.
- Recursive solver walks global cell position `0..total_cells`. At each position, `remaining_in_bar = cells_per_bar - (pos % cells_per_bar)`; only templates with `length_cells <= remaining_in_bar` may be placed (templates never cross a barline).
- Candidates = each `MVP_CATALOG` template in both orientations (original + `mirrored()`), order shuffled by `random.Random(seed)` for variety/reproducibility.
- **Accents are resolved at placement time** (positions are known), so the rule check sees final accents. `is_strong = (pos + k) % cells_per_bar in strong_cells`.
- After building a candidate's strokes, check `find_violations(tail2 + new_strokes) == []` where `tail2` is the last two already-placed strokes (boundary check; interior of each template is pre-validated).
- On success, slice the flat stroke list into bars of `cells_per_bar` and build `Bar`/`Phrase`.

- [ ] **Step 1: Write the failing tests `backend/tests/test_generator.py`**

```python
from fractions import Fraction

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from drumgen.domain.enums import AccentMode
from drumgen.domain.models import TimeSignature
from drumgen.generator import GenerateRequest, GenerationError, generate
from drumgen.rules import find_violations


def _req(**kw: object) -> GenerateRequest:
    base: dict[str, object] = dict(
        time_sig=TimeSignature(num=4, den=4),
        num_bars=1,
        min_subdivision=Fraction(1, 16),
        tempo_bpm=100,
        accent_mode=AccentMode.RUDIMENT,
        seed=1,
    )
    base.update(kw)
    return GenerateRequest.model_validate(base)


def test_generate_fills_bar_exactly():
    phrase = generate(_req())
    total = sum((s.duration for b in phrase.bars for s in b.strokes), Fraction(0))
    assert total == Fraction(4, 4)
    assert all(s.duration == Fraction(1, 16) for b in phrase.bars for s in b.strokes)


def test_generate_output_has_no_rule_violations():
    strokes = [s for b in generate(_req()).bars for s in b.strokes]
    assert find_violations(strokes) == []


def test_generate_multi_bar():
    phrase = generate(_req(num_bars=4))
    assert len(phrase.bars) == 4


def test_generate_rejects_non_integer_grid():
    # 3/8 bar with triplet-16th 1/24 grid -> (3/8)/(1/24) = 9 -> ok; use a mismatch instead
    with pytest.raises(GenerationError):
        generate(_req(time_sig=TimeSignature(num=3, den=8), min_subdivision=Fraction(1, 5)))


def test_seed_is_reproducible():
    a = generate(_req(seed=42)).model_dump(mode="json")
    b = generate(_req(seed=42)).model_dump(mode="json")
    assert a == b


def test_metric_mode_accents_downbeats():
    phrase = generate(_req(accent_mode=AccentMode.METRIC, min_subdivision=Fraction(1, 4)))
    # 4/4 with quarter grid: 4 cells, strong cell is index 0 of the bar
    accents = [s.accent for s in phrase.bars[0].strokes]
    assert accents[0] is True


@settings(max_examples=25, deadline=None)
@given(
    num=st.sampled_from([2, 3, 4]),
    num_bars=st.integers(min_value=1, max_value=3),
    mode=st.sampled_from(list(AccentMode)),
    seed=st.integers(min_value=0, max_value=1000),
)
def test_property_always_valid(num: int, num_bars: int, mode: AccentMode, seed: int):
    phrase = generate(
        _req(
            time_sig=TimeSignature(num=num, den=4),
            num_bars=num_bars,
            min_subdivision=Fraction(1, 16),
            accent_mode=mode,
            seed=seed,
        )
    )
    strokes = [s for b in phrase.bars for s in b.strokes]
    assert find_violations(strokes) == []
    for bar in phrase.bars:
        total = sum((s.duration for s in bar.strokes), Fraction(0))
        assert total == bar.time_sig.bar_length
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_generator.py -q`
Expected: FAIL — `ModuleNotFoundError: drumgen.generator`.

- [ ] **Step 3: Implement `backend/src/drumgen/generator.py`**

```python
import random
from fractions import Fraction

from pydantic import BaseModel

from drumgen.catalog import MVP_CATALOG, RudimentTemplate
from drumgen.domain.enums import AccentMode
from drumgen.domain.models import Bar, Phrase, Stroke, TimeSignature
from drumgen.domain.fractions import FractionField
from drumgen.rules import find_violations


class GenerationError(Exception):
    pass


class GenerateRequest(BaseModel):
    time_sig: TimeSignature
    num_bars: int
    min_subdivision: FractionField
    tempo_bpm: int
    accent_mode: AccentMode
    seed: int | None = None


def _metric_strong_cells(time_sig: TimeSignature, subdivision: Fraction) -> set[int]:
    cells_per_beat = time_sig.beat_length / subdivision
    if cells_per_beat.denominator != 1:
        return {0}
    step = cells_per_beat.numerator
    cells_per_bar = time_sig.bar_length / subdivision
    n = cells_per_bar.numerator
    return {i for i in range(n) if i % step == 0}


def _resolve_accent(template_accent: bool, is_strong: bool, mode: AccentMode) -> bool:
    if mode is AccentMode.RUDIMENT:
        return template_accent
    if mode is AccentMode.METRIC:
        return is_strong
    return template_accent or is_strong


def _candidates(seed: int | None) -> list[RudimentTemplate]:
    pool: list[RudimentTemplate] = []
    for t in MVP_CATALOG:
        pool.append(t)
        pool.append(t.mirrored())
    random.Random(seed).shuffle(pool)
    return pool


def generate(req: GenerateRequest) -> Phrase:
    subdivision = req.min_subdivision
    cells_ratio = req.time_sig.bar_length / subdivision
    if cells_ratio.denominator != 1 or cells_ratio.numerator < 1:
        msg = f"bar {req.time_sig.bar_length} not divisible by subdivision {subdivision}"
        raise GenerationError(msg)
    if req.num_bars < 1:
        msg = "num_bars must be >= 1"
        raise GenerationError(msg)

    cells_per_bar = cells_ratio.numerator
    total_cells = cells_per_bar * req.num_bars
    strong = _metric_strong_cells(req.time_sig, subdivision)
    pool = _candidates(req.seed)

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

    def solve(pos: int, placed: list[Stroke]) -> list[Stroke] | None:
        if pos == total_cells:
            return placed
        remaining_in_bar = cells_per_bar - (pos % cells_per_bar)
        for template in pool:
            if template.length_cells > remaining_in_bar:
                continue
            new_strokes = build(template, pos)
            if find_violations(placed[-2:] + new_strokes):
                continue
            result = solve(pos + template.length_cells, placed + new_strokes)
            if result is not None:
                return result
        return None

    flat = solve(0, [])
    if flat is None:
        msg = "no valid tiling found for the given parameters"
        raise GenerationError(msg)

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_generator.py -q && uv run pyright && uv run ruff check .`
Expected: all pass (including the Hypothesis property test); pyright `0 errors`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/drumgen/generator.py backend/tests/test_generator.py
git commit -m "feat(generator): backtracking solver with accent modes and rule guarantees"
```

---

## Task 8: FastAPI endpoints

**Files:**
- Create: `backend/src/drumgen/api.py`
- Test: `backend/tests/test_api.py`

**Interfaces:**
- Consumes: `generate`, `GenerateRequest`, `GenerationError` (Task 7); `MVP_CATALOG` (Task 6).
- Produces: FastAPI `app` with:
  - `POST /generate` — body = `GenerateRequest` JSON → `200` with `Phrase` JSON; `422` on invalid parameters (from `GenerationError`, mapped via handler).
  - `GET /rudiments` → `200` list of `{id, name, length_cells}` for `MVP_CATALOG`.
  - CORS enabled for `http://localhost:5173` (Vite dev server).

- [ ] **Step 1: Write the failing tests `backend/tests/test_api.py`**

```python
from fastapi.testclient import TestClient

from drumgen.api import app

client = TestClient(app)


def test_generate_endpoint_returns_phrase():
    resp = client.post(
        "/generate",
        json={
            "time_sig": {"num": 4, "den": 4},
            "num_bars": 1,
            "min_subdivision": "1/16",
            "tempo_bpm": 100,
            "accent_mode": "rudiment",
            "seed": 1,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["bars"]) == 1
    assert body["bars"][0]["strokes"][0]["duration"] == "1/16"


def test_generate_endpoint_invalid_grid_returns_422():
    resp = client.post(
        "/generate",
        json={
            "time_sig": {"num": 3, "den": 8},
            "num_bars": 1,
            "min_subdivision": "1/5",
            "tempo_bpm": 100,
            "accent_mode": "rudiment",
        },
    )
    assert resp.status_code == 422


def test_rudiments_endpoint():
    resp = client.get("/rudiments")
    assert resp.status_code == 200
    ids = {r["id"] for r in resp.json()}
    assert "single" in ids and "single-paradiddle" in ids
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_api.py -q`
Expected: FAIL — `ModuleNotFoundError: drumgen.api`.

- [ ] **Step 3: Implement `backend/src/drumgen/api.py`**

```python
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from drumgen.catalog import MVP_CATALOG
from drumgen.domain.models import Phrase
from drumgen.generator import GenerateRequest, GenerationError, generate

app = FastAPI(title="Drum Pattern Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(GenerationError)
async def _generation_error_handler(_request: Request, exc: GenerationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.post("/generate", response_model=Phrase)
def post_generate(req: GenerateRequest) -> Phrase:
    return generate(req)


@app.get("/rudiments")
def get_rudiments() -> list[dict[str, object]]:
    return [
        {"id": t.id, "name": t.name, "length_cells": t.length_cells} for t in MVP_CATALOG
    ]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest -q && uv run pyright && uv run ruff check . && uv run ruff format --check .`
Expected: full backend suite passes; pyright `0 errors`.

- [ ] **Step 5: Commit**

```bash
git add backend/src/drumgen/api.py backend/tests/test_api.py
git commit -m "feat(api): POST /generate and GET /rudiments with CORS"
```

---

## Task 9: Frontend scaffold (Vue 3 + Vite + TS strict + Vitest)

**Files:**
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/main.ts`, `frontend/src/App.vue`, `frontend/src/lib/__tests__/smoke.test.ts`

**Interfaces:**
- Produces: runnable `npm run dev` (port 5173), `npm run build` (`vue-tsc && vite build`), `npm run test` (Vitest).

- [ ] **Step 1: Create `frontend/package.json`**

```json
{
  "name": "drumgen-frontend",
  "private": true,
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vue-tsc -b && vite build",
    "test": "vitest run",
    "typecheck": "vue-tsc --noEmit"
  },
  "dependencies": {
    "vexflow": "^4.2.3",
    "tone": "^14.7.77",
    "vue": "^3.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^5.0.0",
    "typescript": "^5.4.0",
    "vite": "^5.2.0",
    "vitest": "^1.6.0",
    "vue-tsc": "^2.0.0"
  }
}
```

- [ ] **Step 2: Create `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "jsx": "preserve",
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "types": ["vitest/globals"]
  },
  "include": ["src"]
}
```

- [ ] **Step 3: Create `frontend/vite.config.ts`**

```ts
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue()],
  test: { globals: true, environment: 'node' },
})
```

- [ ] **Step 4: Create `frontend/index.html`**

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Drum Pattern Generator</title>
  </head>
  <body>
    <div id="app"></div>
    <script type="module" src="/src/main.ts"></script>
  </body>
</html>
```

- [ ] **Step 5: Create `frontend/src/main.ts` and `frontend/src/App.vue`**

`frontend/src/main.ts`:
```ts
import { createApp } from 'vue'
import App from './App.vue'

createApp(App).mount('#app')
```
`frontend/src/App.vue`:
```vue
<script setup lang="ts">
</script>

<template>
  <main><h1>Drum Pattern Generator</h1></main>
</template>
```

- [ ] **Step 6: Create smoke test `frontend/src/lib/__tests__/smoke.test.ts`**

```ts
import { describe, expect, it } from 'vitest'

describe('smoke', () => {
  it('runs', () => {
    expect(1 + 1).toBe(2)
  })
})
```

- [ ] **Step 7: Install and verify**

Run:
```bash
cd frontend && npm install && npm run test && npm run typecheck
```
Expected: Vitest reports `1 passed`; `vue-tsc` reports no errors.

- [ ] **Step 8: Commit**

```bash
git add frontend/package.json frontend/tsconfig.json frontend/vite.config.ts frontend/index.html frontend/src frontend/package-lock.json
git commit -m "chore(frontend): scaffold Vue 3 + Vite + TS strict + Vitest"
```

---

## Task 10: Phrase types + audio schedule (pure) with Vitest

**Files:**
- Create: `frontend/src/types.ts`
- Create: `frontend/src/lib/audio.ts`
- Test: `frontend/src/lib/__tests__/audio.test.ts`

**Interfaces:**
- Produces:
  - `types.ts`: `Stroke` (`{duration: string; hand: 'L'|'R'; accent: boolean; articulation: string; surface: string}`), `Bar` (`{time_sig: {num:number;den:number}; strokes: Stroke[]}`), `Phrase` (`{time_sig; tempo_bpm:number; subdivision:string; accent_mode:string; bars: Bar[]}`).
  - `audio.ts`: `parseFraction(s: string): number`, `scheduleTimes(phrase: Phrase): {timeSec: number; velocity: number; hand: 'L'|'R'}[]` (pure; accent velocity 1.0, non-accent 0.6; time = cumulative-duration-in-whole-notes × (240 / tempo_bpm) seconds, since one whole note = 4 quarters = 4 × 60/bpm).

- [ ] **Step 1: Write the failing test `frontend/src/lib/__tests__/audio.test.ts`**

```ts
import { describe, expect, it } from 'vitest'

import type { Phrase } from '../../types'
import { parseFraction, scheduleTimes } from '../audio'

const phrase: Phrase = {
  time_sig: { num: 2, den: 4 },
  tempo_bpm: 60,
  subdivision: '1/4',
  accent_mode: 'rudiment',
  bars: [
    {
      time_sig: { num: 2, den: 4 },
      strokes: [
        { duration: '1/4', hand: 'R', accent: true, articulation: 'normal', surface: 'snare' },
        { duration: '1/4', hand: 'L', accent: false, articulation: 'normal', surface: 'snare' },
      ],
    },
  ],
}

describe('parseFraction', () => {
  it('parses n/d', () => {
    expect(parseFraction('1/4')).toBe(0.25)
  })
})

describe('scheduleTimes', () => {
  it('computes absolute times and velocities', () => {
    const events = scheduleTimes(phrase)
    // at 60 bpm a quarter = 1s; first stroke at t=0, second at t=1s
    expect(events.map((e) => e.timeSec)).toEqual([0, 1])
    expect(events.map((e) => e.velocity)).toEqual([1.0, 0.6])
    expect(events.map((e) => e.hand)).toEqual(['R', 'L'])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test`
Expected: FAIL — cannot resolve `../audio` / `../../types`.

- [ ] **Step 3: Implement `frontend/src/types.ts`**

```ts
export interface Stroke {
  duration: string
  hand: 'L' | 'R'
  accent: boolean
  articulation: string
  surface: string
}

export interface Bar {
  time_sig: { num: number; den: number }
  strokes: Stroke[]
}

export interface Phrase {
  time_sig: { num: number; den: number }
  tempo_bpm: number
  subdivision: string
  accent_mode: string
  bars: Bar[]
}
```

- [ ] **Step 4: Implement `frontend/src/lib/audio.ts` (pure part)**

```ts
import type { Phrase } from '../types'

export function parseFraction(s: string): number {
  const [num, den] = s.split('/').map(Number)
  return num / den
}

export interface ScheduledStroke {
  timeSec: number
  velocity: number
  hand: 'L' | 'R'
}

export function scheduleTimes(phrase: Phrase): ScheduledStroke[] {
  const wholeNoteSec = (240 / phrase.tempo_bpm) // 4 quarters * (60/bpm)
  const events: ScheduledStroke[] = []
  let elapsedWhole = 0
  for (const bar of phrase.bars) {
    for (const stroke of bar.strokes) {
      events.push({
        timeSec: elapsedWhole * wholeNoteSec,
        velocity: stroke.accent ? 1.0 : 0.6,
        hand: stroke.hand,
      })
      elapsedWhole += parseFraction(stroke.duration)
    }
  }
  return events
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd frontend && npm run test && npm run typecheck`
Expected: pass; no type errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types.ts frontend/src/lib/audio.ts frontend/src/lib/__tests__/audio.test.ts
git commit -m "feat(frontend): Phrase types + pure audio scheduling"
```

---

## Task 11: Score mapping (Phrase -> VexFlow primitives, pure) with Vitest

**Files:**
- Create: `frontend/src/lib/score.ts`
- Test: `frontend/src/lib/__tests__/score.test.ts`

**Interfaces:**
- Consumes: `Phrase`, `Bar` (Task 10).
- Produces:
  - `vexDuration(subdivision: string): string` — maps a fraction to VexFlow duration code: `"1/4"→"q"`, `"1/8"→"8"`, `"1/16"→"16"`, `"1/32"→"32"`, `"1/12"→"8"` (triplet eighth base), `"1/24"→"16"`, `"1/2"→"h"`, `"1"→"w"`. Throws on unsupported.
  - `barToNoteSpecs(bar: Bar): {duration: string; accent: boolean; sticking: 'L'|'R'}[]` — one entry per stroke; `duration` is the VexFlow code from `vexDuration(stroke.duration)`.

  (This isolates all VexFlow *data* mapping into pure, testable functions; the actual `Vex.Flow` rendering call lives in the component in Task 12 and is not unit-tested.)

- [ ] **Step 1: Write the failing test `frontend/src/lib/__tests__/score.test.ts`**

```ts
import { describe, expect, it } from 'vitest'

import type { Bar } from '../../types'
import { barToNoteSpecs, vexDuration } from '../score'

describe('vexDuration', () => {
  it('maps common durations', () => {
    expect(vexDuration('1/4')).toBe('q')
    expect(vexDuration('1/8')).toBe('8')
    expect(vexDuration('1/16')).toBe('16')
    expect(vexDuration('1/12')).toBe('8')
  })

  it('throws on unsupported', () => {
    expect(() => vexDuration('1/7')).toThrow()
  })
})

describe('barToNoteSpecs', () => {
  it('produces one spec per stroke', () => {
    const bar: Bar = {
      time_sig: { num: 1, den: 4 },
      strokes: [
        { duration: '1/4', hand: 'R', accent: true, articulation: 'normal', surface: 'snare' },
      ],
    }
    expect(barToNoteSpecs(bar)).toEqual([{ duration: 'q', accent: true, sticking: 'R' }])
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npm run test`
Expected: FAIL — cannot resolve `../score`.

- [ ] **Step 3: Implement `frontend/src/lib/score.ts`**

```ts
import type { Bar } from '../types'

const DURATION_MAP: Record<string, string> = {
  '1': 'w',
  '1/2': 'h',
  '1/4': 'q',
  '1/8': '8',
  '1/16': '16',
  '1/32': '32',
  '1/12': '8', // eighth-note triplet base
  '1/24': '16', // sixteenth-note triplet base
  '1/6': 'q', // quarter-note triplet base
}

export function vexDuration(subdivision: string): string {
  const code = DURATION_MAP[subdivision]
  if (code === undefined) {
    throw new Error(`unsupported duration: ${subdivision}`)
  }
  return code
}

export interface NoteSpec {
  duration: string
  accent: boolean
  sticking: 'L' | 'R'
}

export function barToNoteSpecs(bar: Bar): NoteSpec[] {
  return bar.strokes.map((s) => ({
    duration: vexDuration(s.duration),
    accent: s.accent,
    sticking: s.hand,
  }))
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npm run test && npm run typecheck`
Expected: pass; no type errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/score.ts frontend/src/lib/__tests__/score.test.ts
git commit -m "feat(frontend): pure Phrase->VexFlow duration/notespec mapping"
```

---

## Task 12: UI components + wiring (form, score render, playback)

**Files:**
- Create: `frontend/src/components/GenerationForm.vue`
- Create: `frontend/src/components/ScoreView.vue`
- Create: `frontend/src/components/PlayerControls.vue`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/lib/audio.ts` (add Tone.js player)

**Interfaces:**
- Consumes: `Phrase` (Task 10), `scheduleTimes` (Task 10), `barToNoteSpecs`/`vexDuration` (Task 11).
- Produces:
  - `GenerationForm.vue` — emits `generate` with `{time_sig:{num,den}, num_bars, min_subdivision, tempo_bpm, accent_mode, seed?}`; posts to `http://localhost:8000/generate` on submit and emits the resulting `Phrase` via `update:phrase`.
  - `ScoreView.vue` — prop `phrase: Phrase | null`; renders each bar with VexFlow (`Renderer`, `Stave`, `StaveNote` on a single-line percussion clef, `Annotation` under each note with `R`/`L`, accent `Articulation('a>')` on accented notes). Re-renders on prop change.
  - `PlayerControls.vue` — prop `phrase: Phrase | null`; `Play`/`Stop` buttons; on Play calls `playPhrase(phrase)` from `audio.ts` (must be triggered by the click to satisfy Web Audio autoplay policy).
  - `audio.ts` adds `playPhrase(phrase: Phrase): Promise<void>` and `stopPhrase(): void` using Tone.js `NoiseSynth` + a filter, scheduling each event from `scheduleTimes` on `Tone.getTransport()`.

  (Rendering and audio playback are integration code exercised manually via `npm run dev`; unit tests remain on the pure functions from Tasks 10–11.)

- [ ] **Step 1: Add Tone.js player to `frontend/src/lib/audio.ts`**

Append:
```ts
import * as Tone from 'tone'

let synth: Tone.NoiseSynth | null = null

function getSynth(): Tone.NoiseSynth {
  if (synth === null) {
    synth = new Tone.NoiseSynth({
      noise: { type: 'white' },
      envelope: { attack: 0.001, decay: 0.08, sustain: 0 },
    })
    const filter = new Tone.Filter(3000, 'bandpass').toDestination()
    synth.connect(filter)
  }
  return synth
}

export async function playPhrase(phrase: Phrase): Promise<void> {
  await Tone.start()
  const transport = Tone.getTransport()
  stopPhrase()
  const s = getSynth()
  for (const event of scheduleTimes(phrase)) {
    transport.schedule((time) => {
      s.triggerAttackRelease('16n', time, undefined, event.velocity)
    }, event.timeSec)
  }
  transport.start()
}

export function stopPhrase(): void {
  const transport = Tone.getTransport()
  transport.stop()
  transport.cancel(0)
}
```

- [ ] **Step 2: Verify pure tests still pass and types compile**

Run: `cd frontend && npm run test && npm run typecheck`
Expected: pass (existing Vitest tests unaffected); no type errors.

- [ ] **Step 3: Create `frontend/src/components/GenerationForm.vue`**

```vue
<script setup lang="ts">
import { reactive } from 'vue'

import type { Phrase } from '../types'

const emit = defineEmits<{ (e: 'update:phrase', phrase: Phrase): void }>()

const form = reactive({
  num: 4,
  den: 4,
  num_bars: 1,
  min_subdivision: '1/16',
  tempo_bpm: 100,
  accent_mode: 'rudiment',
})

const error = reactive({ message: '' })

async function submit(): Promise<void> {
  error.message = ''
  const resp = await fetch('http://localhost:8000/generate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      time_sig: { num: form.num, den: form.den },
      num_bars: form.num_bars,
      min_subdivision: form.min_subdivision,
      tempo_bpm: form.tempo_bpm,
      accent_mode: form.accent_mode,
    }),
  })
  if (!resp.ok) {
    error.message = `Generation failed (${resp.status})`
    return
  }
  emit('update:phrase', (await resp.json()) as Phrase)
}
</script>

<template>
  <form @submit.prevent="submit">
    <label>Beats <input v-model.number="form.num" type="number" min="1" /></label>
    <label>/ <input v-model.number="form.den" type="number" min="1" /></label>
    <label>Bars <input v-model.number="form.num_bars" type="number" min="1" /></label>
    <label>
      Subdivision
      <select v-model="form.min_subdivision">
        <option value="1/8">1/8</option>
        <option value="1/16">1/16</option>
        <option value="1/12">triplet 1/12</option>
      </select>
    </label>
    <label>Tempo <input v-model.number="form.tempo_bpm" type="number" min="20" /></label>
    <label>
      Accents
      <select v-model="form.accent_mode">
        <option value="rudiment">rudiment</option>
        <option value="metric">metric</option>
        <option value="both">both</option>
      </select>
    </label>
    <button type="submit">Generate</button>
    <p v-if="error.message" role="alert">{{ error.message }}</p>
  </form>
</template>
```

- [ ] **Step 4: Create `frontend/src/components/ScoreView.vue`**

```vue
<script setup lang="ts">
import { Accidental, Annotation, Formatter, Renderer, Stave, StaveNote } from 'vexflow'
import { ref, watch } from 'vue'

import { barToNoteSpecs } from '../lib/score'
import type { Phrase } from '../types'

const props = defineProps<{ phrase: Phrase | null }>()
const container = ref<HTMLDivElement | null>(null)

function render(phrase: Phrase): void {
  const host = container.value
  if (host === null) return
  host.innerHTML = ''
  const renderer = new Renderer(host, Renderer.Backends.SVG)
  const width = 260 * phrase.bars.length
  renderer.resize(width, 160)
  const context = renderer.getContext()

  phrase.bars.forEach((bar, index) => {
    const stave = new Stave(10 + index * 260, 40, 250)
    if (index === 0) stave.addClef('percussion').addTimeSignature(`${bar.time_sig.num}/${bar.time_sig.den}`)
    stave.setContext(context).draw()

    const notes = barToNoteSpecs(bar).map((spec) => {
      const note = new StaveNote({ keys: ['b/4'], duration: spec.duration })
      note.addModifier(new Annotation(spec.sticking).setVerticalJustification(Annotation.VerticalJustify.BOTTOM))
      if (spec.accent) note.addModifier(new (Annotation as unknown as typeof Accidental)('>'))
      return note
    })
    Formatter.FormatAndDraw(context, stave, notes)
  })
}

watch(
  () => props.phrase,
  (phrase) => {
    if (phrase !== null) render(phrase)
  },
  { immediate: true },
)
</script>

<template>
  <div ref="container" />
</template>
```

Note to implementer: VexFlow's modifier API for accents varies by minor version. If `Articulation('a>')` is available in the installed VexFlow, prefer:
`import { Articulation } from 'vexflow'` and `note.addModifier(new Articulation('a>').setPosition(3))`. Verify against the installed version at `npm run dev` and use whichever the version exposes; the accent glyph is the only affected detail.

- [ ] **Step 5: Create `frontend/src/components/PlayerControls.vue`**

```vue
<script setup lang="ts">
import { playPhrase, stopPhrase } from '../lib/audio'
import type { Phrase } from '../types'

const props = defineProps<{ phrase: Phrase | null }>()

async function onPlay(): Promise<void> {
  if (props.phrase !== null) await playPhrase(props.phrase)
}
</script>

<template>
  <div>
    <button :disabled="phrase === null" @click="onPlay">Play</button>
    <button @click="stopPhrase">Stop</button>
  </div>
</template>
```

- [ ] **Step 6: Wire up `frontend/src/App.vue`**

```vue
<script setup lang="ts">
import { ref } from 'vue'

import GenerationForm from './components/GenerationForm.vue'
import PlayerControls from './components/PlayerControls.vue'
import ScoreView from './components/ScoreView.vue'
import type { Phrase } from './types'

const phrase = ref<Phrase | null>(null)
</script>

<template>
  <main>
    <h1>Drum Pattern Generator</h1>
    <GenerationForm @update:phrase="phrase = $event" />
    <ScoreView :phrase="phrase" />
    <PlayerControls :phrase="phrase" />
  </main>
</template>
```

- [ ] **Step 7: Typecheck, build, and manual smoke test**

Run:
```bash
cd frontend && npm run typecheck && npm run build
```
Expected: `vue-tsc` no errors; `vite build` succeeds.

Manual: in one terminal `cd backend && uv run uvicorn drumgen.api:app --port 8000`; in another `cd frontend && npm run dev`. Open `http://localhost:5173`, click Generate → notation appears; click Play → pattern is audible.

- [ ] **Step 8: Commit**

```bash
git add frontend/src
git commit -m "feat(frontend): form + VexFlow score + Tone.js playback wired end-to-end"
```

---

## Task 13: Root README with run instructions

**Files:**
- Create: `README.md`

**Interfaces:** none (documentation).

- [ ] **Step 1: Write `README.md`**

```markdown
# Drum Pattern Generator

Generates valid snare-drum rudiment patterns, renders them as notation, and plays them back.

## Backend

    cd backend
    uv sync
    uv run pytest
    uv run uvicorn drumgen.api:app --reload --port 8000

## Frontend

    cd frontend
    npm install
    npm run dev   # http://localhost:5173

## Quality gates

- Backend: `uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run pytest`
- Frontend: `npm run typecheck && npm run test && npm run build`

See `docs/superpowers/specs/2026-07-29-drum-pattern-generator-design.md` for the design.
```

- [ ] **Step 2: Commit**

```bash
git add README.md
git commit -m "docs: root README with run and quality-gate instructions"
```

---

## Self-Review

**Spec coverage:**
- Spec §2 (durations/meter/invariant) → Tasks 2, 4. ✔
- Spec §3 (Pydantic models, Fraction as "n/d", enums) → Tasks 2, 3, 4. ✔
- Spec §4 (catalog, mvp/violates flags, single+double atomics, paradiddles, rolls) → Task 6. ✔
- Spec §5 (R1/R2 on main notes) → Task 5; enforced in generator Task 7. ✔
- Spec §6 (backtracking, inputs, accent modes, seed, guarantee/error) → Task 7. ✔
- Spec §7 (FastAPI /generate + /rudiments, CORS; Vue/VexFlow/Tone.js; monorepo) → Tasks 8, 9, 10, 11, 12. ✔
- Spec §8 (uv, ruff strict, pyright strict, pytest+hypothesis property tests, Vitest on pure fns, TestClient) → Tasks 1, 7, 8, 10, 11. ✔
- Spec §9/§10 (phase-2 deferrals, no-rudiment-filter assumption) → respected: buzz/flam/drag/LLM/multi-surface absent; generator draws from full MVP_CATALOG with no user filter. ✔

**Placeholder scan:** No TBD/TODO/"handle edge cases" — every code step contains complete code. ✔

**Type consistency:** `GenerateRequest`/`generate`/`GenerationError` names consistent across Tasks 7–8. `Phrase`/`Bar`/`Stroke` field names identical in backend models (Task 4), frontend types (Task 10), and mappers (Tasks 10–11). `scheduleTimes`/`playPhrase`/`stopPhrase` consistent across Tasks 10, 12. `barToNoteSpecs`/`vexDuration` consistent across Tasks 11, 12. `FractionField` reused Tasks 2, 4, 7. ✔

**Known implementation risk flagged inline:** VexFlow accent-modifier API varies by minor version (noted in Task 12 Step 4) — the only detail requiring version verification during manual smoke.
