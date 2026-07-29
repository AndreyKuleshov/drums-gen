# Backend Tasks 1-8 Implementation Report

Branch: `feat/drum-gen-mvp`
Scope: `backend/` only (drum pattern generator MVP — scaffold, FractionField, enums,
domain models, rules validator, catalog, generator, FastAPI).

## Overall Status: DONE

All 8 tasks implemented TDD-style (failing test confirmed, then implementation,
then green), one commit per task. Final full-gate command is green with zero
errors/warnings.

## Final full-gate output

Command:
```
cd backend && uv run pytest -q && uv run ruff check . && uv run ruff format --check . && uv run pyright
```

Output:
```
...............................                                          [100%]
31 passed in 4.13s
All checks passed!
16 files already formatted
0 errors, 0 warnings, 0 informations
```

- pytest: 31 passed (includes the Hypothesis property-based test in
  `test_generator.py`, `max_examples=25`)
- ruff check: all checks passed (strict rule set: E,F,I,N,UP,B,A,C4,SIM,RUF,ANN,PT)
- ruff format --check: all files already formatted
- pyright (strict mode): 0 errors, 0 warnings, 0 informations

## Per-task status

### Task 1 — Backend scaffold
Status: DONE (commit `56e9525`, plus follow-up `455a122`)
- Created `backend/pyproject.toml`, `backend/pyrightconfig.json`,
  `backend/src/drumgen/__init__.py`, `backend/src/drumgen/domain/__init__.py`,
  `backend/tests/test_smoke.py` exactly per plan.
- `uv sync` installed 27 packages (pydantic 2.13.4, fastapi 0.140.13, pytest 9.1.1,
  hypothesis 6.163.0, ruff 0.16.0, pyright 1.1.411, etc.) — all pinned lower
  bounds from the plan, resolved to latest compatible versions.
- Deviation: `git add -A`-equivalent from the plan's suggested `git add` list
  accidentally included compiled `__pycache__/*.pyc` files (no `.gitignore`
  existed yet at that point in the plan). Added `backend/.gitignore`
  (`__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `.venv/`,
  `*.egg-info/`) and removed the committed pycache files in a small follow-up
  commit `455a122`. This is a hygiene fix, not a plan deviation in behavior.

### Task 2 — FractionField
Status: DONE (commit `1add1fc`)
- Implemented `backend/src/drumgen/domain/fractions.py` exactly as specified:
  `Annotated[Fraction, PlainValidator, PlainSerializer, WithJsonSchema]`.
- Verified the "known risk": `model_json_schema()` returns
  `{"type": "string", ...}` correctly, and `model_dump(mode="json")` serializes
  to `"1/12"` string form. Roundtrip via `model_validate` confirmed to work
  under pydantic 2.13.4.
- Deviation: pyright strict flagged `_M(d="1/12")` / `_M(d=1)` — passing a bare
  `str`/`int` literal directly to the pydantic-generated `__init__` — as
  `reportArgumentType`, because pyright's dataclass-transform for
  `BaseModel.__init__` types the parameter from the bare annotation type
  (`Fraction`), not from what `PlainValidator` accepts at runtime. This is a
  known pydantic/pyright limitation, not a bug in the FractionField code
  itself. Fixed by changing those two test calls to
  `_M.model_validate({"d": "1/12"})` / `_M.model_validate({"d": 1})` (the dict
  value type is `Any`, so pyright doesn't flag it) — same runtime coverage of
  string/int coercion, zero change to the `FractionField` implementation or
  its public interface.

### Task 3 — Enums
Status: DONE (commit `457a7da`)
- Implemented `Hand`, `Articulation`, `Surface`, `AccentMode` with the exact
  values/names specified.
- Deviation: ruff's `UP042` rule flags `class X(str, Enum)` in favor of
  `enum.StrEnum` (available since Python 3.12, which this project targets).
  Switched all four enums to inherit from `StrEnum` instead of `(str, Enum)`.
  Behavior, `.value`, and JSON serialization are identical — pydantic and
  `str` comparisons work the same way.

### Task 4 — Domain models
Status: DONE (commit `eb9db6e`)
- Implemented `TimeSignature` (`.bar_length`, `.beat_length`, `.is_compound()`),
  `Stroke`, `Bar` (with `model_validator(mode="after")` bar-length invariant),
  `Phrase` exactly per plan.
- Deviation: same class of pyright issue as Task 2 — test code that passed
  bare string literals (`hand="R"`, `accent_mode="rudiment"`) directly to
  pydantic constructors for `Hand`/`AccentMode` enum fields tripped
  `reportArgumentType` under strict mode (annotation-based param typing again).
  Fixed by using the enum members directly (`Hand.R`, `Hand.L`,
  `AccentMode.RUDIMENT`) in the test file instead of raw strings — same test
  coverage of the bar-length invariant and JSON roundtrip, no change to
  `models.py`.

### Task 5 — Sticking-rule validator
Status: DONE (commit `13c58aa`)
- Implemented `RuleViolation`, `find_violations`, `is_valid` in
  `backend/src/drumgen/rules.py` exactly per plan (R1: accent-after-unaccent
  same hand; R2: three-in-a-row same hand).
- No deviations; the plan's test helper `_s(hand: str, ...)` was adjusted to
  `_s(hand: Hand, ...)` and callers updated to pass `Hand.R`/`Hand.L` (for the
  same pyright reason as above), preserving all 5 original test cases and
  assertions unchanged in intent.

### Task 6 — Rudiment catalog
Status: DONE (commit `263494e`)
- Implemented `RudimentElement`, `RudimentTemplate` (`.length_cells`,
  `.mirrored()`), `MVP_CATALOG` (8 templates), `FULL_CATALOG` (+ flagged
  `triple-stroke`) exactly per plan's stickings.
- Deviation: `ruff format` reformatted one line in `mirrored()` (collapsed a
  list comprehension onto one line, within the 100-char limit) — pure
  formatting, no logic change.
- All 5 catalog tests pass, including the R2 violation check on the flagged
  `triple-stroke` template and mirrored-hand-swap check on
  `single-paradiddle`.

### Task 7 — Deterministic generator
Status: DONE (commit `20c5cad`)
- Implemented `GenerationError`, `GenerateRequest`, `generate()`,
  `_metric_strong_cells`, `_resolve_accent`, backtracking `solve()` exactly per
  plan's design notes (candidates = MVP_CATALOG × {original, mirrored},
  shuffled by `random.Random(seed)`; boundary-only rule check against
  `placed[-2:] + new_strokes`; templates never cross a barline).
- All 7 tests pass, including the Hypothesis property test (`max_examples=25`,
  varying meter numerator, bar count, accent mode, seed) asserting
  `find_violations == []` and exact bar-length fill for every generated
  phrase.
- Deviation: minor internal change from `placed + new_strokes` (plan's literal
  code) to `[*placed, *new_strokes]` — functionally identical list
  concatenation; picked up incidentally, no behavioral difference. Also fixed
  ruff `C408` (`dict(...)` call) in the test helper by rewriting as a dict
  literal — same test data, no logic change.

### Task 8 — FastAPI endpoints
Status: DONE (commit `180b8cb`)
- Implemented `POST /generate` (200 → `Phrase` JSON, `GenerationError` → 422
  via exception handler), `GET /rudiments` (200 → list of
  `{id, name, length_cells}`), CORS for `http://localhost:5173`, exactly per
  plan.
- All 3 API tests pass (happy path, invalid-grid 422, rudiments listing).
- Deviations (two, both required to reach a clean strict-pyright gate):
  1. Renamed `_generation_error_handler` → `generation_error_handler`.
     Pyright strict flagged the underscore-prefixed, decorator-only-registered
     function as `reportUnusedFunction` (it's never called directly in code,
     only invoked by FastAPI's exception-handling machinery at runtime).
     Dropping the leading underscore satisfies pyright's private-symbol
     unused-check without changing behavior — FastAPI resolves the handler by
     decorator registration regardless of the name.
  2. Added `httpx2` as a dev dependency. Root cause: the installed
     `starlette` (1.3.1, pulled in transitively by the pinned
     `fastapi>=0.110`) does `import httpx2 as httpx` under `TYPE_CHECKING` in
     `starlette/testclient.py`, falling back to `httpx` only at runtime if
     `httpx2` isn't installed (`httpx2` is a newer, actively-typed fork/rename
     of `httpx`, matching a `StarletteDeprecationWarning` we saw before the
     fix: *"Using httpx with starlette.testclient is deprecated; install
     httpx2 instead"*). Without `httpx2` present, pyright can't resolve the
     type-only import and everything routed through `TestClient.post/get`
     (i.e. every response object in `test_api.py`) degraded to `Unknown`,
     producing ~15 `reportUnknownVariableType`/`reportUnknownMemberType`
     errors. Installing `httpx2>=0.28` (already resolvable from PyPI) fixed
     both the pyright errors and the runtime deprecation warning, with zero
     change to `api.py`'s public interface (`app`, `POST /generate`,
     `GET /rudiments` routes unchanged).

## Deviations summary (all preserve public interfaces / JSON shapes)

| # | File(s) | Change | Reason |
|---|---|---|---|
| 1 | `backend/.gitignore` (new) | ignore `__pycache__`, `.pytest_cache`, etc. | accidental pycache commit in Task 1 |
| 2 | `tests/test_fractions.py` | 2 calls switched to `.model_validate({...})` | pyright strict: `PlainValidator` widens runtime input but not the pydantic-generated `__init__` param type |
| 3 | `domain/enums.py` | `(str, Enum)` → `StrEnum` | ruff `UP042` |
| 4 | `tests/test_models.py`, `tests/test_rules.py` | string literals → enum members (`Hand.R`, `AccentMode.RUDIMENT`) | same pyright strict issue as #2, for plain enum fields |
| 5 | `catalog.py` | one line reformatted | `ruff format` |
| 6 | `generator.py`, `tests/test_generator.py` | `placed + new_strokes` → `[*placed, *new_strokes]`; `dict(...)` → dict literal | incidental / ruff `C408` |
| 7 | `api.py` | `_generation_error_handler` → `generation_error_handler` | pyright `reportUnusedFunction` on underscore-prefixed decorator target |
| 8 | `pyproject.toml`, `uv.lock` | added `httpx2>=0.28` dev dependency | pyright strict: starlette's `TYPE_CHECKING` import of `httpx2` was unresolvable, degrading TestClient response types to `Unknown` |

None of these changes altered any public interface, field name, JSON key, HTTP
route, status code, or response shape specified in the plan's Interfaces
blocks.

## Commits (chronological)

| short hash | message |
|---|---|
| `56e9525` | chore(backend): scaffold uv + ruff strict + pyright strict + pytest |
| `455a122` | chore(backend): add .gitignore, drop committed pycache |
| `1add1fc` | feat(domain): FractionField pydantic type serializing to n/d |
| `457a7da` | feat(domain): Hand/Articulation/Surface/AccentMode enums |
| `eb9db6e` | feat(domain): TimeSignature/Stroke/Bar/Phrase with bar-length invariant |
| `13c58aa` | feat(rules): R1/R2 sticking-rule validator on main notes |
| `263494e` | feat(catalog): MVP rudiment templates + flagged triple-stroke |
| `20c5cad` | feat(generator): backtracking solver with accent modes and rule guarantees |
| `180b8cb` | feat(api): POST /generate and GET /rudiments with CORS |

## Notes for whoever picks up Tasks 9-12 (frontend)

- `backend/` is fully self-contained; nothing outside `backend/` was touched.
- The JSON wire format is exactly as specified: durations serialize as
  `"num/den"` strings (e.g. `"1/16"`), enums serialize as their string values
  (`"R"`/`"L"`, `"normal"`, `"snare"`, `"rudiment"`/`"metric"`/`"both"`), and
  the `/generate` and `/rudiments` response shapes match the plan's Task 8
  Interfaces block verbatim.

---

## Code-review fix pass (2026-07-29)

Branch: `feat/drum-gen-mvp`, scope: `backend/` only.

### FIX 1 (Important) — non-positive subdivision → GenerationError (422), not 500 ZeroDivisionError
`generate()` in `src/drumgen/generator.py` now raises `GenerationError` immediately when
`subdivision <= 0`, before the `cells_ratio = req.time_sig.bar_length / subdivision` division
that previously raised an unhandled `ZeroDivisionError` (surfaced as a 500 through FastAPI).
Tests added:
- `tests/test_generator.py::test_generate_rejects_nonpositive_subdivision`
- `tests/test_api.py::test_generate_endpoint_nonpositive_subdivision_returns_422`

### FIX 2 (Important) — `_metric_strong_cells` silent `{0}` fallback removed
Replaced the old approach (compute `cells_per_beat = beat_length / subdivision`, and silently
fall back to `{0}` whenever that ratio wasn't an integer — silently mismarking metric strength
for compound/irregular meters) with a direct per-cell position check: cell `i` is strong iff
`(subdivision * i) / beat_length` is an integer (denominator == 1). This correctly handles
compound meters (e.g. 6/8) where each cell's absolute position must land on a beat boundary,
rather than relying on a fixed step derived from a possibly-non-integer ratio.
Tests added:
- `tests/test_generator.py::test_metric_strong_cells_simple_meter` (4/4, 1/8 grid → {0,2,4,6})
- `tests/test_generator.py::test_metric_strong_cells_compound_meter` (6/8, 1/8 grid → {0,3})

### FIX 3 (Minor) — bound `tempo_bpm` and `num_bars`
`GenerateRequest` (defined in `src/drumgen/generator.py`, not `domain/models.py`) now declares
`tempo_bpm: int = Field(ge=1)` and `num_bars: int = Field(ge=1)`, imported `Field` from
pydantic. The existing `num_bars < 1` runtime guard in `generate()` is kept as defense-in-depth
for direct construction paths. No public JSON key, route, or interface signature changed other
than adding these validation bounds.
Test added:
- `tests/test_api.py::test_generate_endpoint_nonpositive_tempo_returns_422`

### Notes
- `tests/test_generator.py` imports the private `_metric_strong_cells` directly for unit
  testing; added `# pyright: ignore[reportPrivateUsage]` on that import line to keep strict
  pyright clean without weakening the module's public/private boundary.

### Verify (all green)
```
cd /Users/greenolls/cursor/drum-gen/backend && uv run pytest tests/test_generator.py tests/test_api.py -q && uv run ruff check . && uv run ruff format --check . && uv run pyright
```
Output:
```
...............                                                          [100%]
15 passed in 0.52s
All checks passed!
16 files already formatted
0 errors, 0 warnings, 0 informations
```
Full backend suite (sanity check): `36 passed`.
