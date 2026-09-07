# Pattern Generator 2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a parallel "Patterns 2.0" generator that packs rudimental sticking blocks (accented singles, odd 3/5/7 groupings, paradiddles) edge-to-edge to fill N bars, enforcing two hard rules, on a new UI tab — leaving the existing generators untouched.

**Architecture:** New backend module `sticking_generator.py` produces the existing `Phrase` model via a seeded backtracking packer; a new `POST /patterns2/generate` endpoint returns it. The `Stroke` model gains an additive `ghost: bool = False`. A new `/patterns2` Vue route reuses `TransportRack` (playback via `playPhrase`) and `ScoreView` (notation, extended to show ghost notes). Old generators/endpoints/tabs are not modified.

**Tech Stack:** Python 3.12, Pydantic v2, FastAPI, pytest; Vue 3 + TypeScript, VexFlow, Tone.js, Vitest.

## Global Constraints

- Two hard rules over the full note stream (including block seams):
  1. **Adjacent accents alternate hands** — if notes *i* and *i+1* are both accents, they must be different hands.
  2. **Ghosts cap at two per hand in a row** — no run of 3+ consecutive ghost notes on the same hand.
- Every note is **accent xor ghost** (no third dynamic level).
- Vocabulary stored canonically R-lead; L-lead derived by swapping `R`↔`L`.
- Deterministic: same request + `seed` → identical `Phrase`.
- Isolation: only additive shared edits allowed — `Stroke.ghost` (default `False`) and ghost rendering in `ScoreView.vue`. Do **not** modify `generator.py`, `groove_generator.py`, `fill_seeds.py`, or their endpoints.
- v1 subdivisions: `1/8` and `1/16` only. Default meter `4/4`.
- All gates green before PR: `make lint-backend` (ruff + pyright strict), `uv run pytest`, `npm run typecheck`, `npx vitest run`.
- Backend commands run from `backend/`; frontend from `frontend/`.

---

## File Structure

**Backend**
- Modify `backend/src/drumgen/domain/models.py` — add `Stroke.ghost: bool = False`.
- Create `backend/src/drumgen/sticking_generator.py` — vocabulary, mirroring, rules, packer, `StickingRequest`, `generate_sticking`.
- Modify `backend/src/drumgen/api.py` — add `POST /patterns2/generate`.
- Create `backend/tests/test_sticking.py` — generator + rules tests.
- Modify `backend/tests/` (existing) — none; `Stroke.ghost` default keeps old output identical.

**Frontend**
- Modify `frontend/src/types.ts` — add `Stroke.ghost: boolean`.
- Modify `frontend/src/lib/score.ts` — `NoteSpec.ghost` + map it.
- Modify `frontend/src/lib/audio.ts` — ghost velocity in `scheduleTimes`.
- Modify `frontend/src/components/ScoreView.vue` — ghost noteheads + lowercase sticking for ghosts.
- Create `frontend/src/views/Patterns2View.vue` — the new tab.
- Modify `frontend/src/router/index.ts` — add `/patterns2` route.
- Modify `frontend/src/views/StudioView.vue` — add a nav link to the new tab.
- Create `frontend/src/lib/score.spec.ts` and `frontend/src/lib/audio.spec.ts` — vitest.

---

## Task 1: Add `ghost` to the Stroke model

**Files:**
- Modify: `backend/src/drumgen/domain/models.py`
- Test: `backend/tests/test_sticking_model.py` (create)

**Interfaces:**
- Produces: `Stroke` gains field `ghost: bool = False` (used by Tasks 3, 5, 6).

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_sticking_model.py`:

```python
from drumgen.domain.enums import Hand
from drumgen.domain.models import Stroke


def test_stroke_ghost_defaults_false():
    s = Stroke(duration="1/16", hand=Hand.R)
    assert s.ghost is False


def test_stroke_ghost_can_be_set():
    s = Stroke(duration="1/16", hand=Hand.L, ghost=True)
    assert s.ghost is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_sticking_model.py -v`
Expected: FAIL — `TypeError`/`ValidationError` for unexpected keyword `ghost`.

- [ ] **Step 3: Add the field**

In `backend/src/drumgen/domain/models.py`, inside `class Stroke`, add after the `accent` field:

```python
    ghost: bool = False
    """True for a ghost note (played soft). Mutually exclusive with `accent`.
    Defaults False so existing generators are unaffected."""
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_sticking_model.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Verify existing generators are unchanged**

Run: `cd backend && uv run pytest -q`
Expected: PASS (all existing tests still green).

- [ ] **Step 6: Commit**

```bash
git add backend/src/drumgen/domain/models.py backend/tests/test_sticking_model.py
git commit -m "feat(patterns2): add additive Stroke.ghost field"
```

---

## Task 2: Vocabulary, mirroring, and rule checks

**Files:**
- Create: `backend/src/drumgen/sticking_generator.py`
- Test: `backend/tests/test_sticking.py` (create)

**Interfaces:**
- Produces (consumed by Task 3):
  - `Note = tuple[str, bool]` — `(hand, is_accent)`, `hand` in `{"R","L"}`.
  - `Block = tuple[Note, ...]`.
  - `Family = Literal["singles", "odd", "paradiddle"]`.
  - `VOCAB: dict[Family, tuple[Block, ...]]` — canonical R-lead blocks.
  - `mirror(block: Block) -> Block` — swaps R↔L.
  - `rules_hold(stream: Sequence[Note]) -> bool` — both hard rules.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_sticking.py`:

```python
from drumgen.sticking_generator import VOCAB, mirror, rules_hold


def test_vocab_has_three_families_with_expected_lengths():
    assert set(VOCAB) == {"singles", "odd", "paradiddle"}
    lengths = {fam: sorted(len(b) for b in blocks) for fam, blocks in VOCAB.items()}
    assert lengths["singles"] == [1, 2, 3, 4]
    assert lengths["odd"] == [3, 5, 7]
    assert lengths["paradiddle"] == [4, 6, 6]


def test_every_canonical_block_is_individually_legal():
    for blocks in VOCAB.values():
        for block in blocks:
            assert rules_hold(block), block


def test_mirror_swaps_hands_and_preserves_accents():
    block = VOCAB["odd"][0]  # Rll -> (('R',True),('L',False),('L',False))
    assert mirror(block) == (("L", True), ("R", False), ("R", False))
    # Mirrors are also legal.
    for blocks in VOCAB.values():
        for block in blocks:
            assert rules_hold(mirror(block))


def test_rule1_adjacent_accents_must_alternate():
    # two adjacent accents, same hand -> illegal
    assert not rules_hold(((("R", True)), ("R", True)))
    # adjacent accents, different hands -> legal
    assert rules_hold((("R", True), ("L", True)))
    # two same-hand accents split by a ghost -> legal (RlR...)
    assert rules_hold((("R", True), ("L", False), ("R", True)))


def test_rule2_no_more_than_two_ghosts_per_hand_in_a_row():
    assert rules_hold((("R", True), ("L", False), ("L", False)))  # 2 ghosts ok
    assert not rules_hold((("R", True), ("L", False), ("L", False), ("L", False)))  # 3 ghosts
    # ghost hand change resets the run
    assert rules_hold((("L", False), ("L", False), ("R", False), ("R", False)))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_sticking.py -v`
Expected: FAIL — `ModuleNotFoundError: drumgen.sticking_generator`.

- [ ] **Step 3: Write the vocabulary + helpers**

Create `backend/src/drumgen/sticking_generator.py`:

```python
"""Pattern Generator 2.0 — sticking-block phrase generator.

Packs a small vocabulary of rudimental blocks (accented singles, odd 3/5/7
groupings, paradiddles) edge-to-edge to fill N bars, enforcing two rules across
the whole stream:

  1. Adjacent accents alternate hands.
  2. No more than two consecutive ghost notes on the same hand.

Every note is either an accent (uppercase) or a ghost (lowercase). Blocks are
stored canonically R-lead; the L-lead form is `mirror()`. Output is the existing
monophonic `Phrase` model, so it renders and plays through the same components.
"""

from collections.abc import Sequence
from typing import Literal

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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_sticking.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Lint**

Run: `cd .. && make lint-backend`
Expected: `All checks passed!` and `0 errors` from pyright.

- [ ] **Step 6: Commit**

```bash
git add backend/src/drumgen/sticking_generator.py backend/tests/test_sticking.py
git commit -m "feat(patterns2): sticking vocabulary, mirroring, rule checks"
```

---

## Task 3: Seeded packer and `generate_sticking`

**Files:**
- Modify: `backend/src/drumgen/sticking_generator.py`
- Test: `backend/tests/test_sticking.py`

**Interfaces:**
- Consumes: `VOCAB`, `mirror`, `rules_hold`, `Note`, `Block`, `Family` (Task 2); `GenerationError` from `drumgen.generator`; `Phrase`, `Bar`, `Stroke`, `TimeSignature` from `drumgen.domain.models`; `Hand`, `AccentMode` from `drumgen.domain.enums`; `FractionField`.
- Produces (consumed by Task 4):
  - `class StickingRequest(BaseModel)` with fields `time_sig: TimeSignature`, `num_bars: int` (ge=1, le=64), `subdivision: FractionField`, `tempo_bpm: int` (ge=1), `singles: bool = True`, `odd: bool = True`, `paradiddle: bool = True`, `seed: int | None = None`.
  - `generate_sticking(req: StickingRequest) -> Phrase`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_sticking.py`:

```python
from fractions import Fraction

import pytest

from drumgen.domain.enums import Hand
from drumgen.domain.models import TimeSignature
from drumgen.generator import GenerationError
from drumgen.sticking_generator import StickingRequest, generate_sticking

_44 = TimeSignature(num=4, den=4)


def _req(**kw) -> StickingRequest:
    base = dict(time_sig=_44, num_bars=1, subdivision="1/16", tempo_bpm=100)
    base.update(kw)
    return StickingRequest(**base)


def _stream(phrase):
    return [
        (s.hand.value, s.accent)
        for bar in phrase.bars
        for s in bar.strokes
    ]


def test_fills_exact_note_count_per_bar():
    phrase = generate_sticking(_req(num_bars=2, subdivision="1/16", seed=1))
    assert len(phrase.bars) == 2
    for bar in phrase.bars:
        assert len(bar.strokes) == 16  # 4/4 at 1/16
        assert all(s.duration == Fraction(1, 16) for s in bar.strokes)


def test_every_note_is_accent_xor_ghost():
    phrase = generate_sticking(_req(num_bars=4, seed=3))
    for bar in phrase.bars:
        for s in bar.strokes:
            assert s.accent != s.ghost  # exactly one is true


@pytest.mark.parametrize("seed", range(30))
def test_generated_phrase_always_satisfies_both_rules(seed):
    phrase = generate_sticking(_req(num_bars=4, subdivision="1/16", seed=seed))
    from drumgen.sticking_generator import rules_hold

    assert rules_hold(_stream(phrase))


def test_family_toggles_are_respected_singles_only():
    # Singles are all accents; with only singles enabled, no ghosts appear.
    phrase = generate_sticking(_req(num_bars=2, singles=True, odd=False, paradiddle=False, seed=5))
    assert all(s.accent and not s.ghost for bar in phrase.bars for s in bar.strokes)


def test_each_family_alone_can_fill_a_bar():
    for fam in ("singles", "odd", "paradiddle"):
        kw = {"singles": False, "odd": False, "paradiddle": False, fam: True}
        phrase = generate_sticking(_req(num_bars=1, subdivision="1/16", seed=2, **kw))
        assert len(phrase.bars[0].strokes) == 16


def test_deterministic_for_a_fixed_seed():
    a = generate_sticking(_req(num_bars=3, seed=42)).model_dump()
    b = generate_sticking(_req(num_bars=3, seed=42)).model_dump()
    assert a == b


def test_eighth_subdivision_uses_eight_notes_per_bar():
    phrase = generate_sticking(_req(num_bars=1, subdivision="1/8", seed=1))
    assert len(phrase.bars[0].strokes) == 8
    assert all(s.duration == Fraction(1, 8) for s in phrase.bars[0].strokes)


def test_no_family_enabled_raises():
    with pytest.raises(GenerationError):
        generate_sticking(_req(singles=False, odd=False, paradiddle=False))


def test_subdivision_that_does_not_divide_the_bar_raises():
    with pytest.raises(GenerationError):
        generate_sticking(_req(time_sig=TimeSignature(num=3, den=4), subdivision="1/8", num_bars=1))
        # 3/4 at 1/8 = 6 notes/bar -> fine; use a bad one instead:
```

Fix the last test to use a genuinely non-dividing case:

```python
def test_subdivision_that_does_not_divide_the_bar_raises():
    # 4/4 bar length 1; subdivision 1/3 does not divide it into whole notes.
    with pytest.raises(GenerationError):
        generate_sticking(_req(subdivision="1/3"))
```

(Delete the earlier draft of `test_subdivision_that_does_not_divide_the_bar_raises`; keep only this one.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_sticking.py -v`
Expected: FAIL — `ImportError: cannot import name 'StickingRequest'`.

- [ ] **Step 3: Implement the request model, packer, and builder**

Append to `backend/src/drumgen/sticking_generator.py`:

```python
import random
from fractions import Fraction

from pydantic import BaseModel, Field

from drumgen.domain.enums import AccentMode, Hand
from drumgen.domain.fractions import FractionField
from drumgen.domain.models import Bar, Phrase, Stroke, TimeSignature
from drumgen.generator import GenerationError

_FAMILY_FLAGS: tuple[Family, ...] = ("singles", "odd", "paradiddle")


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
    enabled = [fam for fam in _FAMILY_FLAGS if getattr(req, fam)]
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
```

Note: move the new `import` lines to the top of the file with the Task 2 imports (ruff will flag mid-file imports). Final import block at the top should be:

```python
import random
from collections.abc import Sequence
from fractions import Fraction
from typing import Literal

from pydantic import BaseModel, Field

from drumgen.domain.enums import AccentMode, Hand
from drumgen.domain.fractions import FractionField
from drumgen.domain.models import Bar, Phrase, Stroke, TimeSignature
from drumgen.generator import GenerationError
```

(`Fraction` is used only if you keep a Fraction reference; it is imported for clarity and may be removed if unused — let ruff guide you.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_sticking.py -v`
Expected: PASS (all sticking tests, including the 30 parametrized rule checks).

- [ ] **Step 5: Lint (fix any unused import, e.g. `Fraction`)**

Run: `cd .. && make lint-backend`
Expected: `All checks passed!`, `0 errors`. If ruff flags an unused `Fraction`, delete that import line and re-run.

- [ ] **Step 6: Commit**

```bash
git add backend/src/drumgen/sticking_generator.py backend/tests/test_sticking.py
git commit -m "feat(patterns2): seeded backtracking packer -> Phrase"
```

---

## Task 4: API endpoint `POST /patterns2/generate`

**Files:**
- Modify: `backend/src/drumgen/api.py`
- Test: `backend/tests/test_patterns2_api.py` (create)

**Interfaces:**
- Consumes: `generate_sticking`, `StickingRequest` (Task 3).
- Produces: `POST /patterns2/generate` returning a `Phrase` JSON.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_patterns2_api.py`:

```python
from fastapi.testclient import TestClient

from drumgen.api import app

client = TestClient(app)


def _body(**kw):
    base = {
        "time_sig": {"num": 4, "den": 4},
        "num_bars": 2,
        "subdivision": "1/16",
        "tempo_bpm": 110,
    }
    base.update(kw)
    return base


def test_generate_returns_a_phrase():
    resp = client.post("/patterns2/generate", json=_body(seed=1))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["bars"]) == 2
    assert len(data["bars"][0]["strokes"]) == 16
    # ghost field is present on strokes
    assert "ghost" in data["bars"][0]["strokes"][0]


def test_no_family_enabled_returns_422():
    resp = client.post(
        "/patterns2/generate",
        json=_body(singles=False, odd=False, paradiddle=False),
    )
    assert resp.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && uv run pytest tests/test_patterns2_api.py -v`
Expected: FAIL — 404 for `/patterns2/generate`.

- [ ] **Step 3: Add the endpoint**

In `backend/src/drumgen/api.py`:

Add to the imports near the top:

```python
from drumgen.sticking_generator import StickingRequest, generate_sticking
```

Add the route after the existing `post_generate` handler:

```python
@app.post("/patterns2/generate", response_model=Phrase)
def post_generate_patterns2(req: StickingRequest) -> Phrase:
    return generate_sticking(req)
```

(The existing `generation_error_handler` already maps `GenerationError` → 422, and `generate_sticking` raises that same class, so no new handler is needed.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && uv run pytest tests/test_patterns2_api.py -v`
Expected: PASS (2 tests).

- [ ] **Step 5: Full backend gate**

Run: `cd .. && make lint-backend && cd backend && uv run pytest -q`
Expected: lint clean; all backend tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/drumgen/api.py backend/tests/test_patterns2_api.py
git commit -m "feat(patterns2): POST /patterns2/generate endpoint"
```

---

## Task 5: Frontend data — ghost in types, score specs, and velocity

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/lib/score.ts`
- Modify: `frontend/src/lib/audio.ts`
- Test: `frontend/src/lib/score.spec.ts` (create), `frontend/src/lib/audio.spec.ts` (create)

**Interfaces:**
- Produces (consumed by Task 6, 7): `Stroke.ghost: boolean`; `NoteSpec.ghost: boolean`; `scheduleTimes` velocity = `1.0` accent / `0.3` ghost / `0.6` otherwise.

- [ ] **Step 1: Write the failing tests**

Create `frontend/src/lib/score.spec.ts`:

```ts
import { describe, expect, it } from 'vitest'

import { barToNoteSpecs } from './score'
import type { Bar } from '../types'

const bar: Bar = {
  time_sig: { num: 4, den: 4 },
  strokes: [
    { duration: '1/16', hand: 'R', accent: true, ghost: false, articulation: 'normal', surface: 'snare', grace: 0, group: 0 },
    { duration: '1/16', hand: 'L', accent: false, ghost: true, articulation: 'normal', surface: 'snare', grace: 0, group: 0 },
  ],
}

describe('barToNoteSpecs', () => {
  it('carries the ghost flag through to the note spec', () => {
    const specs = barToNoteSpecs(bar)
    expect(specs[0].ghost).toBe(false)
    expect(specs[1].ghost).toBe(true)
  })
})
```

Create `frontend/src/lib/audio.spec.ts`:

```ts
import { describe, expect, it } from 'vitest'

import { scheduleTimes } from './audio'
import type { Phrase } from '../types'

const phrase: Phrase = {
  time_sig: { num: 4, den: 4 },
  tempo_bpm: 120,
  subdivision: '1/16',
  accent_mode: 'rudiment',
  bars: [
    {
      time_sig: { num: 4, den: 4 },
      strokes: [
        { duration: '1/16', hand: 'R', accent: true, ghost: false, articulation: 'normal', surface: 'snare', grace: 0, group: 0 },
        { duration: '1/16', hand: 'L', accent: false, ghost: true, articulation: 'normal', surface: 'snare', grace: 0, group: 0 },
        { duration: '1/16', hand: 'R', accent: false, ghost: false, articulation: 'normal', surface: 'snare', grace: 0, group: 0 },
      ],
    },
  ],
}

describe('scheduleTimes velocity', () => {
  it('is loud for accents, soft for ghosts, medium otherwise', () => {
    const [acc, ghost, normal] = scheduleTimes(phrase)
    expect(acc.velocity).toBe(1.0)
    expect(ghost.velocity).toBe(0.3)
    expect(normal.velocity).toBe(0.6)
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/lib/score.spec.ts src/lib/audio.spec.ts`
Expected: FAIL — type error / `ghost` undefined on spec; ghost velocity `0.6` not `0.3`.

- [ ] **Step 3a: Add `ghost` to the Stroke type**

In `frontend/src/types.ts`, inside `interface Stroke`, after `accent: boolean`:

```ts
  /** True for a ghost note (played soft). Mutually exclusive with `accent`. */
  ghost: boolean
```

- [ ] **Step 3b: Carry `ghost` through NoteSpec**

In `frontend/src/lib/score.ts`, in `interface NoteSpec` add after `accent: boolean`:

```ts
  /** True for a ghost note; rendered with a parenthesized notehead. */
  ghost: boolean
```

In `barToNoteSpecs`, add `ghost: s.ghost,` to the returned object.

- [ ] **Step 3c: Ghost velocity in scheduleTimes**

In `frontend/src/lib/audio.ts`, in `scheduleTimes`, replace the `velocity` line:

```ts
        velocity: stroke.accent ? 1.0 : 0.6,
```

with:

```ts
        velocity: stroke.accent ? 1.0 : stroke.ghost ? 0.3 : 0.6,
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/lib/score.spec.ts src/lib/audio.spec.ts`
Expected: PASS.

- [ ] **Step 5: Typecheck**

Run: `cd frontend && npm run typecheck`
Expected: no errors. (Existing code that builds `Stroke` objects — none in the frontend does directly except tests/fixtures — remains valid; the backend supplies `ghost`.)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types.ts frontend/src/lib/score.ts frontend/src/lib/audio.ts frontend/src/lib/score.spec.ts frontend/src/lib/audio.spec.ts
git commit -m "feat(patterns2): thread ghost through types, score specs, velocity"
```

---

## Task 6: ScoreView renders ghost notes

**Files:**
- Modify: `frontend/src/components/ScoreView.vue`

**Interfaces:**
- Consumes: `NoteSpec.ghost` (Task 5).
- Produces: ghost notes render with a lowercase sticking label and parentheses around the notehead.

- [ ] **Step 1: Lowercase sticking for ghosts**

In `frontend/src/components/ScoreView.vue`, in `render`, replace the Annotation line:

```ts
      note.addModifier(
        new Annotation(spec.sticking).setVerticalJustification(AnnotationVerticalJustify.BOTTOM),
      )
```

with:

```ts
      const label = spec.ghost ? spec.sticking.toLowerCase() : spec.sticking
      note.addModifier(
        new Annotation(label).setVerticalJustification(AnnotationVerticalJustify.BOTTOM),
      )
```

- [ ] **Step 2: Parenthesize ghost noteheads**

In the same `render` function, after the manual-accents block (after the `if (accentIdx.length > 0) { ... }` block, before `for (const note of notes) noteEls.push(...)`), add:

```ts
    // Ghost notes: parentheses around the notehead, drawn manually (consistent
    // with the manual accent marks above) so no extra VexFlow modifier is needed.
    const ghostIdx = specs.flatMap((s, i) => (s.ghost ? [i] : []))
    if (ghostIdx.length > 0) {
      context.setFont('Georgia, serif', 15, 'normal')
      for (const i of ghostIdx) {
        const x = notes[i].getAbsoluteX()
        const y = notes[i].getYs()[0]
        context.fillText('(', x - 9, y + 5)
        context.fillText(')', x + 7, y + 5)
      }
    }
```

- [ ] **Step 3: Typecheck**

Run: `cd frontend && npm run typecheck`
Expected: no errors. (`getYs()` and `getAbsoluteX()` exist on VexFlow `StaveNote`.)

- [ ] **Step 4: Manual visual check (deferred to Task 7)**

Ghost rendering is verified end-to-end once the tab exists (Task 7). No unit test here — VexFlow draws to a canvas/SVG that jsdom can't meaningfully assert. Proceed.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/ScoreView.vue
git commit -m "feat(patterns2): render ghost noteheads + lowercase sticking"
```

---

## Task 7: The Patterns 2.0 tab (view + route + nav)

**Files:**
- Create: `frontend/src/views/Patterns2View.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/views/StudioView.vue`
- Test: `frontend/src/views/Patterns2View.spec.ts` (create)

**Interfaces:**
- Consumes: `apiFetch` (`/patterns2/generate`), `playPhrase`/`stopPhrase`, `TransportRack` + `PlayEngine`, `ScoreView`, `Phrase`.

- [ ] **Step 1: Write the failing mount test**

Create `frontend/src/views/Patterns2View.spec.ts`:

```ts
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

// Stub network + audio so the component mounts in jsdom.
vi.mock('../lib/api', () => ({
  apiFetch: vi.fn().mockResolvedValue({
    time_sig: { num: 4, den: 4 },
    tempo_bpm: 100,
    subdivision: '1/16',
    accent_mode: 'rudiment',
    bars: [],
  }),
}))
vi.mock('../lib/audio', () => ({ playPhrase: vi.fn(), stopPhrase: vi.fn() }))

import Patterns2View from './Patterns2View.vue'

describe('Patterns2View', () => {
  it('renders the three family toggles and a generate button', () => {
    const wrapper = mount(Patterns2View, {
      global: { stubs: { RouterLink: true } },
    })
    const text = wrapper.text()
    expect(text).toContain('Singles')
    expect(text).toContain('Paradiddle')
    expect(wrapper.find('[data-test="generate"]').exists()).toBe(true)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/views/Patterns2View.spec.ts`
Expected: FAIL — cannot resolve `./Patterns2View.vue`.

- [ ] **Step 3: Create the view**

Create `frontend/src/views/Patterns2View.vue`:

```vue
<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import ScoreView from '../components/ScoreView.vue'
import TransportRack from '../components/TransportRack.vue'
import type { PlayEngine } from '../components/TransportRack.vue'
import { apiFetch } from '../lib/api'
import { playPhrase, stopPhrase } from '../lib/audio'
import { persistedRef } from '../lib/storage'
import type { Phrase } from '../types'

const tempo = persistedRef('patterns2-tempo', 100)
const bars = persistedRef('patterns2-bars', 2)
const subdivision = persistedRef('patterns2-sub', '1/16')
const singles = persistedRef('patterns2-singles', true)
const odd = persistedRef('patterns2-odd', true)
const paradiddle = persistedRef('patterns2-paradiddle', true)

const phrase = ref<Phrase | null>(null)
const activeStep = ref<number | null>(null)
const error = ref('')

const transport = ref<InstanceType<typeof TransportRack> | null>(null)
const canPlay = computed(() => phrase.value !== null)
const meter = { num: 4, den: 4 }

const engine: PlayEngine = {
  play: async (o) => {
    if (phrase.value !== null) await playPhrase(phrase.value, o)
  },
  stop: stopPhrase,
}

async function generate(): Promise<void> {
  error.value = ''
  if (!singles.value && !odd.value && !paradiddle.value) {
    error.value = 'Enable at least one block family.'
    return
  }
  try {
    phrase.value = await apiFetch<Phrase>('/patterns2/generate', {
      method: 'POST',
      body: JSON.stringify({
        time_sig: meter,
        num_bars: bars.value,
        subdivision: subdivision.value,
        tempo_bpm: tempo.value,
        singles: singles.value,
        odd: odd.value,
        paradiddle: paradiddle.value,
      }),
    })
  } catch {
    error.value = 'Couldn’t generate. Is the engine running?'
  }
}

function onGlobalKey(e: KeyboardEvent): void {
  if (e.metaKey || e.ctrlKey || e.altKey) return
  const tag = (e.target as HTMLElement | null)?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
  if (e.code === 'Space') {
    e.preventDefault()
    ;(e.target as HTMLElement | null)?.blur?.()
    transport.value?.toggle()
  } else if (e.code === 'KeyR') {
    e.preventDefault()
    transport.value?.toggleLoop()
  } else if (e.code === 'KeyC') {
    e.preventDefault()
    transport.value?.toggleClick()
  } else if (e.code === 'Enter') {
    e.preventDefault()
    void generate()
  }
}

onMounted(() => window.addEventListener('keydown', onGlobalKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onGlobalKey))
</script>

<template>
  <main class="stage">
    <div class="console">
      <header class="console__head">
        <div class="brand">
          <span class="brand__mark" aria-hidden="true">RG</span>
          <span class="brand__name">Patterns 2.0</span>
        </div>
        <div class="brand__meta">
          <RouterLink to="/" class="nav-link">&larr; Studio</RouterLink>
        </div>
      </header>

      <section class="screen" aria-label="Notation display">
        <div class="screen__glass">
          <ScoreView v-if="phrase" :phrase="phrase" :active-step="activeStep" />
          <div v-else class="screen__empty">
            <p class="screen__empty-text">
              Toggle families and hit Generate for a sticking pattern.
            </p>
          </div>
        </div>
      </section>

      <TransportRack
        ref="transport"
        :can-play="canPlay"
        :meter="meter"
        :tempo="tempo"
        :engine="engine"
        @step="activeStep = $event"
      />

      <p v-if="error" class="formmsg--error" role="alert">{{ error }}</p>

      <section class="controls">
        <div class="families" role="group" aria-label="Block families">
          <button type="button" :class="{ on: singles }" @click="singles = !singles">Singles</button>
          <button type="button" :class="{ on: odd }" @click="odd = !odd">Odd 3/5/7</button>
          <button type="button" :class="{ on: paradiddle }" @click="paradiddle = !paradiddle">
            Paradiddle
          </button>
        </div>

        <div class="field">
          <span class="field__label">Subdivision</span>
          <button
            v-for="s in ['1/8', '1/16']"
            :key="s"
            type="button"
            :class="{ on: subdivision === s }"
            @click="subdivision = s"
          >
            {{ s }}
          </button>
        </div>

        <label class="field">
          <span class="field__label">Bars</span>
          <input v-model.number="bars" type="number" min="1" max="16" />
        </label>

        <label class="field">
          <span class="field__label">Tempo</span>
          <input v-model.number="tempo" type="number" min="30" max="300" />
        </label>

        <button class="generate" type="button" data-test="generate" @click="generate">
          Generate
        </button>
      </section>
    </div>
  </main>
</template>

<style scoped>
.controls {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-top: 12px;
}
.families,
.field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.field__label {
  font-family: var(--font-mono);
  font-size: 0.62rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-dim);
}
.controls button {
  padding: 8px 12px;
  border-radius: var(--r-md);
  border: 1px solid var(--edge);
  background: linear-gradient(180deg, var(--raised), var(--panel));
  color: var(--text-dim);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  cursor: pointer;
}
.controls button.on {
  color: var(--amber-bright);
  box-shadow: inset 0 0 0 1px rgba(255, 157, 60, 0.3);
}
.generate {
  margin-left: auto;
  color: var(--amber-bright) !important;
}
.controls input {
  width: 64px;
  padding: 7px 8px;
  border-radius: var(--r-sm);
  border: 1px solid var(--edge);
  background: #100e0c;
  color: var(--text);
  font-family: var(--font-mono);
}
.screen {
  border-radius: var(--r-lg);
  padding: 10px;
  background: linear-gradient(180deg, #0f0d0b, #171310);
  border: 1px solid var(--edge);
}
.screen__glass {
  min-height: 200px;
  border-radius: var(--r-md);
  background: linear-gradient(180deg, #fbf6ec, var(--screen));
  border: 1px solid var(--screen-edge);
  display: flex;
  align-items: center;
}
.screen__empty {
  width: 100%;
  padding: 40px 24px;
  text-align: center;
}
.screen__empty-text {
  color: #6b6252;
}
.formmsg--error {
  color: var(--danger);
  font-size: 0.88rem;
  margin: 0;
}
</style>
```

- [ ] **Step 4: Register the route**

In `frontend/src/router/index.ts`, add to the `routes` array (after the `/rudiments` route):

```ts
    {
      path: '/patterns2',
      name: 'patterns2',
      component: () => import('../views/Patterns2View.vue'),
    },
```

- [ ] **Step 5: Add a nav link from Studio**

In `frontend/src/views/StudioView.vue`, in the header `<div class="brand__meta">`, after the Rudiments link, add:

```vue
          <RouterLink to="/patterns2" class="nav-link">Patterns 2.0 &rarr;</RouterLink>
```

- [ ] **Step 6: Run the mount test**

Run: `cd frontend && npx vitest run src/views/Patterns2View.spec.ts`
Expected: PASS.

- [ ] **Step 7: Full frontend gate**

Run: `cd frontend && npm run typecheck && npx vitest run`
Expected: no type errors; all vitest pass.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/views/Patterns2View.vue frontend/src/views/Patterns2View.spec.ts frontend/src/router/index.ts frontend/src/views/StudioView.vue
git commit -m "feat(patterns2): new /patterns2 tab (controls + transport + score)"
```

---

## Task 8: End-to-end verification

**Files:** none (verification only).

- [ ] **Step 1: Start the stack**

Run (two terminals, from repo root):
`make dev-backend` and `make dev-frontend`
Expected: backend on :8000, frontend on :5173.

- [ ] **Step 2: Probe the endpoint**

Run:
```bash
curl -s -X POST http://localhost:8000/patterns2/generate \
  -H 'Content-Type: application/json' \
  -d '{"time_sig":{"num":4,"den":4},"num_bars":2,"subdivision":"1/16","tempo_bpm":110,"singles":true,"odd":true,"paradiddle":true,"seed":1}' \
  | python3 -m json.tool | head -40
```
Expected: 2 bars × 16 strokes; strokes carry `accent`/`ghost` (exactly one true), `hand` R/L.

- [ ] **Step 3: Drive the UI**

Open `http://localhost:5173/patterns2`. Toggle families, pick subdivision, set bars=2, click Generate (or press Enter). Confirm: notation renders with accents (`>`) on capital-hand notes and parenthesized noteheads with lowercase sticking on ghosts; Space plays (accents loud, ghosts soft); the old Studio tab still works unchanged.

- [ ] **Step 4: Confirm isolation**

Open `http://localhost:5173/` — the Studio (groove + exercise) generates and plays exactly as before. Old endpoints `/generate` and `/pattern/generate` unaffected.

- [ ] **Step 5: Final full gate**

Run: `cd backend && uv run pytest -q && cd .. && make lint-backend && cd frontend && npm run typecheck && npx vitest run`
Expected: all green.

---

## Self-Review

**Spec coverage:**
- Vocabulary (singles/odd/paradiddle, canonical R-lead + mirror) → Task 2. ✅
- Rule 1 (adjacent accents alternate) + Rule 2 (≤2 same-hand ghosts) → Task 2 `rules_hold`, enforced in Task 3 packer, tested across seeds. ✅
- Pack-to-fill-N-bars model → Task 3. ✅
- Family toggles → Task 3 request + Task 7 UI. ✅
- Subdivisions 1/8 & 1/16, default 4/4 → Task 3 + Task 7. ✅
- Backend module + endpoint returning `Phrase`; additive `Stroke.ghost` → Tasks 1, 3, 4. ✅
- New tab reusing TransportRack + ScoreView; snare playback with accent/ghost velocity; ghost notation → Tasks 5, 6, 7. ✅
- Isolation (old generators untouched) → verified Task 8 step 4. ✅

**Placeholder scan:** No TBD/TODO; all steps contain concrete code/commands. The one drafted-then-replaced test (`test_subdivision_that_does_not_divide_the_bar_raises`) has explicit "delete the earlier draft" instruction. ✅

**Type consistency:** `generate_sticking`/`StickingRequest` names match across Tasks 3, 4. `Note`/`Block`/`Family`/`VOCAB`/`mirror`/`rules_hold` consistent across Tasks 2, 3. Frontend `Stroke.ghost` (Task 5) consumed by `NoteSpec.ghost` (Task 5), `ScoreView` (Task 6), and view (Task 7). `PlayEngine` shape matches `TransportRack`. ✅
