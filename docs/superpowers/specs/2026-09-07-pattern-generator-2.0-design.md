# Pattern Generator 2.0 — Sticking-Block Generator

**Date:** 2026-09-07
**Status:** Approved design, pre-implementation
**Author:** Andrey + Claude

## Summary

A new, parallel generator ("Patterns 2.0") that builds **sticking phrases** by
packing a small vocabulary of rudimental blocks — accented singles, odd
groupings (3/5/7), and paradiddles — edge-to-edge to fill N bars exactly, on a
new UI tab. Every note is either an **accent** (written uppercase) or a **ghost
note** (written lowercase). The old generators (rudiment `/generate` and groove
`/pattern/generate`) are left completely untouched; this is additive.

## Goals

- Generate a legal, musical sticking phrase from the block vocabulary.
- Enforce two hard rules across the whole phrase, including block seams.
- Deterministic, seeded, backend-generated, pytest-tested (matches the project's
  existing quality story), rendered and played through the existing frontend
  notation + transport.
- Full isolation from the existing generators; new module, new endpoint, new tab.

## Non-goals (v1 / YAGNI)

- Triplet / compound subdivisions (only 1/8 and 1/16 in v1).
- Orchestration across surfaces (snare only in v1).
- Manual block picking / catalog UI (generation is automatic from family toggles).
- Saving/liking Patterns 2.0 phrases (can come later; reuses `Phrase` so it's
  cheap to add).

## The Two Rules (hard invariants)

Applied to the flat note stream (the whole phrase, across block seams):

1. **Accents alternate when adjacent.** If notes at positions *i* and *i+1* are
   **both accents**, they must be on different hands. Accents separated by at
   least one ghost are unconstrained (so `R l R l l` — two right-hand accents
   split by a ghost — is legal).
2. **No more than two strokes on the same hand in a row — accents and ghosts
   alike.** You can't physically play three in a row with one hand, so a same-hand
   accent must not abut two same-hand ghosts (`R l l` and `l l L` mirror-cases both
   count). (`R l l` is fine; `R l l l` and `l l L` are not.) This is stricter than a
   ghosts-only cap — corrected from the original draft "ghosts cap at two per hand in
   a row" after local testing surfaced a three-same-hand run at a block seam.

No other sticking constraints are imposed (YAGNI).

## Vocabulary

Stored **canonically as R-lead**; the L-lead (mirror) form is derived at runtime
by swapping every `R`↔`L`. Each block is a list of `(hand, is_accent)` pairs.
Uppercase = accent, lowercase = ghost.

| Family | Canonical blocks (length in notes) |
|---|---|
| `singles` (all accents) | `R`(1), `RL`(2), `RLR`(3), `RLRL`(4) |
| `odd` (accent + ghost tail) | `Rll`(3), `RlRll`(5), `RlRlRll`(7) |
| `paradiddle` | `Rlrr`(4), `RlRlrr`(6), `Rlrrll`(6) |

The analyst's original list included both orientations (`RL`/`LR`, `Rlrr`/`Lrll`,
`RlRlrr`/`LrLrll`); these collapse to the canonical set above plus automatic
mirroring.

Each block is individually rule-legal (verified in tests). Rules can still be
violated **at seams**, which is what the generator's search prevents.

## Generation Algorithm

**Inputs** (`StickingRequest`): `time_sig` (default 4/4), `num_bars`,
`subdivision` (`1/8` or `1/16`, default `1/16`), `tempo_bpm`, `families` (three
booleans: `singles`, `odd`, `paradiddle`; at least one true), `seed` (optional).

**Note budget.** `N = num_bars * (bar_length / subdivision)`. Every note occupies
exactly one subdivision slot. Blocks freely cross barlines — the bar is only a
notation-grouping unit, and odd groupings crossing beats/bars is the intended
polyrhythmic feel.

**Search.** Seeded backtracking packer:

```
candidates = [(block, orientation) for block in enabled_families
                                    for orientation in (as_is, mirror)]
build(stream):
  if len(stream) == N: return stream            # success
  for (block, orient) in shuffled(candidates, rng):
      piece = orient(block)
      if len(stream) + len(piece) > N: continue  # would overshoot
      if not rules_hold(stream + piece): continue # rule 1 & 2 across the seam
      result = build(stream + piece)
      if result is not None: return result
  return None                                    # dead end -> backtrack
```

- `rules_hold` only needs to re-check the boundary region (last note of `stream`
  vs first note of `piece`, and within `piece`), but a full re-scan is cheap and
  simpler for v1.
- Randomization comes from `random.Random(seed)` shuffling the candidate order
  each step; determinism holds for a fixed seed.
- Exact fill is guaranteed by the `> N` overshoot guard plus backtracking. If a
  family subset genuinely cannot tile `N` (extremely unlikely given the small
  block lengths and gcd 1 within each family), the generator raises
  `GenerationError` with a clear message, surfaced as HTTP 4xx.

**Output.** The flat stream is sliced into `num_bars` bars of equal duration;
each note becomes a `Stroke{duration=subdivision, hand, accent xor ghost}`.
Returned as a `Phrase` (so it renders/plays through existing components).

## Backend

- **New module** `backend/src/drumgen/sticking_generator.py` — vocabulary,
  mirroring, rule checks, backtracking packer, `StickingRequest` model,
  `generate_sticking(req) -> Phrase`.
- **New endpoint** `POST /patterns2/generate → Phrase` in `api.py`.
- **Shared model change (additive):** `Stroke` gains `ghost: bool = False` in
  `domain/models.py`. Default `False` means the rudiment generator's output is
  byte-for-byte unchanged.
- No edits to `generator.py`, `groove_generator.py`, or their endpoints.

## Frontend

- **New route** `/patterns2` + a nav link labelled **"Patterns 2.0"**.
- **New view** `Patterns2View.vue` reusing:
  - `TransportRack.vue` for play/stop/loop/click and the Space/R/C shortcuts.
  - `ScoreView.vue` for notation (extended to draw ghost noteheads).
- **Controls** (inline in `Patterns2View.vue` for v1; extract to a component
  later if it grows): three family toggles
  (Singles · Odd 3/5/7 · Paradiddles, all on by default), subdivision (1/8 · 1/16),
  bars, tempo, Generate (Enter).
- **Playback:** snare only. Velocity by level — accent ≈ 1.0, ghost ≈ 0.3,
  reusing the snare sample path in `lib/audio.ts` / `lib/kit.ts`.
- **Notation:** `ScoreView` learns to render a ghost note as a **parenthesized
  notehead**, alongside the existing accent `>` marks and R/L sticking labels.
  Sticking labels follow the note's dynamic (uppercase for accents, lowercase for
  ghosts) to match the analyst's written convention. The ghost-rendering code is
  guarded by the presence of `ghost` strokes, so the rudiment path is visually
  unchanged.

## Testing

**Backend (pytest):**
- Each canonical block is individually rule-legal.
- Every generated phrase (across many seeds, families, bars, subdivisions)
  satisfies rules 1 and 2 over the full stream.
- The phrase fills exactly `N` notes / the bar lengths validate.
- Family toggles are respected (only enabled families' blocks appear).
- Determinism: same request+seed → identical `Phrase`.
- Each family alone can fill a 4/4 bar at 1/16.
- Mirroring produces legal L-lead forms.

**Frontend (vitest):** a minimal mount test of the new view + ghost-notehead
rendering path.

**Gates:** `make lint-backend` (ruff + pyright strict), `uv run pytest`,
`npm run typecheck`, `npx vitest run` — all green before PR.

## Isolation Guarantees

The only shared, additive changes:
1. `Stroke.ghost: bool = False` — non-breaking (old output identical).
2. `ScoreView.vue` gains ghost-notehead rendering — additive, guarded.

Everything else is new files or a new route. The old generators, endpoints, and
the existing Studio/Rudiments tabs are untouched.

## Open Defaults (chosen, overridable)

- Tab name **"Patterns 2.0"**, route `/patterns2`.
- v1 subdivisions: **1/8 and 1/16** only.
- Default meter **4/4** (generation itself is meter-agnostic).
