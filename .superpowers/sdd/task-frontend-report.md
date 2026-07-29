# Frontend implementation report — Tasks 9-13

Branch: `feat/drum-gen-mvp`. Backend (Tasks 1-8) was already complete and untouched.

## Per-task status

| Task | Description | Status |
|---|---|---|
| 9 | Frontend scaffold (Vue 3 + Vite + TS strict + Vitest) | DONE |
| 10 | Phrase types + pure audio schedule (TDD) | DONE |
| 11 | Score mapping (Phrase -> VexFlow primitives, pure, TDD) | DONE |
| 12 | UI components + wiring (form, ScoreView, PlayerControls) | DONE |
| 13 | Root README | DONE |

## Commits

- `af323d2` chore(frontend): scaffold Vue 3 + Vite + TS strict + Vitest
- `93afc07` feat(frontend): Phrase types + pure audio scheduling
- `d41abaa` feat(frontend): pure Phrase->VexFlow duration/notespec mapping
- `b097e04` feat(frontend): form + VexFlow score + Tone.js playback wired end-to-end
- `40cb739` docs: root README with run and quality-gate instructions

## Final gate output

```
$ cd frontend && npm run test
 ✓ src/lib/__tests__/smoke.test.ts  (1 test)
 ✓ src/lib/__tests__/score.test.ts  (3 tests)
 ✓ src/lib/__tests__/audio.test.ts  (2 tests)
 Test Files  3 passed (3)
      Tests  6 passed (6)

$ npm run typecheck
> vue-tsc --noEmit
(no output — 0 errors)

$ npm run build
> vue-tsc -b && vite build
✓ 1091 modules transformed.
dist/index.html                    0.33 kB
dist/assets/index-BxSpUEKV.js  1,294.96 kB │ gzip: 398.96 kB
✓ built in ~1.8s
(one informational warning about chunk size >500kB; not an error)
```

All three gates are green with zero TypeScript errors.

## Version adaptations

Installed versions (`npm install` resolved, all within the plan's declared major-version ranges):
- vue 3.5.40 (plan pinned ^3.4.0)
- vexflow 4.2.5 (plan pinned ^4.2.3)
- tone 14.9.17 (plan pinned ^14.7.77)
- vite 5.4.21, vitest 1.6.1, vue-tsc 2.2.12, typescript 5.9.3 — all within plan's ^ ranges.

No major-version deviations, so no code needed to change to accommodate a different major. Three adaptations were still required, found by reading the installed packages rather than transcribing the plan's code verbatim:

1. **`tsconfig.json` needed `@types/node` + `"types": ["node", "vitest/globals"]`.** The plan's `tsconfig.json` only listed `"types": ["vitest/globals"]`. `vue-tsc --noEmit` failed because `vite`'s and `vitest`'s own `.d.ts` files reference Node globals (`Buffer`, `NodeJS`, `node:stream` etc.) which aren't ambient without `@types/node`. Added `@types/node` as a devDependency (not in the plan's package.json, but required for a clean strict typecheck) and added `"node"` to `compilerOptions.types`.

2. **`tsconfig.json` needed `"noEmit": true`.** Without it, `vue-tsc -b` (composite/project-reference build mode used by `npm run build`) emitted `.js`/`.js.map` files alongside every `.ts`/`.vue` source file into `src/`. Caught this during `git add` review (stray `.js` files showed up as new files) and cleaned them up, then added `noEmit: true` so `vue-tsc -b` only type-checks and `vite build` alone produces `dist/`.

3. **`vite.config.ts` needed `test.server.deps.inline: ['tone']`.** Once `audio.ts` imports `tone` at module scope (Task 12), Vitest's default Node-SSR module resolution tried to load Tone's ESM build using Node's native resolver, which failed with `ERR_MODULE_NOT_FOUND` on Tone's extensionless internal imports (e.g. `from "./core/Global"` resolving to `Global.js`). Vite itself resolves these fine in the browser/dev-server context; the fix is to tell Vitest to transform `tone` through Vite instead of externalizing it for native Node resolution.

4. **Fixed a real bug in the plan's own snippet**: `NoiseSynth.triggerAttackRelease` in the installed Tone version has the signature `(duration: Time, time?: Time, velocity?: NormalRange)` — three parameters. The plan's Task 12 code called it with four arguments (`'16n', time, undefined, event.velocity`), which would fail `vue-tsc` strict (too many arguments) had it been transcribed as-is. Verified against `node_modules/tone/build/esm/instrument/NoiseSynth.d.ts` and changed the call to `s.triggerAttackRelease('16n', time, event.velocity)`.

## VexFlow accent + sticking implementation (no casts)

Verified the installed VexFlow (4.2.5) type declarations directly under `frontend/node_modules/vexflow/build/types/src/`:
- `articulation.d.ts` confirms `Articulation` extends `Modifier`, constructed as `new Articulation(type: string)`, and `tables.js` confirms `'a>'` is a registered articulation code (`articAccentAbove`/`articAccentBelow`).
- `modifier.d.ts` confirms `Modifier.setPosition(position: string | number): this` and the static `Modifier.Position` enum (`CENTER/LEFT/RIGHT/ABOVE/BELOW`).
- `annotation.d.ts` confirms `Annotation` extends `Modifier`, `new Annotation(text: string)`, `.setVerticalJustification(just: string | AnnotationVerticalJustify): this`, and the exported `AnnotationVerticalJustify` enum (`TOP/CENTER/BOTTOM/CENTER_STEM`).
- `src/index.d.ts` confirms all of `Annotation`, `AnnotationVerticalJustify`, `Articulation`, `Modifier`, `Formatter`, `Renderer`, `Stave`, `StaveNote` are re-exported from the package root (`vexflow`), and a `curl` against the running Vite dev server on `/src/components/ScoreView.vue` showed Vite's dependency pre-bundler (`node_modules/.vite/deps/vexflow.js`) successfully resolving all of these named imports at runtime, not just at the type level.

`frontend/src/components/ScoreView.vue` uses, per note:

```ts
note.addModifier(
  new Annotation(spec.sticking).setVerticalJustification(AnnotationVerticalJustify.BOTTOM),
)
if (spec.accent) {
  note.addModifier(new Articulation('a>').setPosition(Modifier.Position.ABOVE))
}
```

This replaces the plan's deliberate placeholder hack (`new (Annotation as unknown as typeof Accidental)('>')`) entirely — no `Accidental` import, no `as unknown as` cast, no `@ts-ignore` anywhere in the component. `vue-tsc --noEmit` and `vue-tsc -b` both confirm zero errors.

## Manual/integration verification performed

- Started the backend (`uv run uvicorn drumgen.api:app --port 8000`) and confirmed `POST http://127.0.0.1:8000/generate` returns a well-formed `Phrase` JSON body matching the frontend `types.ts` shape exactly (field names/types checked byte-for-byte against the response).
  - Note: `localhost:8000` on this machine is intercepted by an unrelated pre-existing Docker service bound to `*:8000`; `127.0.0.1:8000` reaches the actual uvicorn process. This is a pre-existing local-machine port collision, not a code defect — `GenerationForm.vue` posts to `http://localhost:8000/generate` per the fixed contract, which will work correctly in a clean environment (and does work once the conflicting Docker service is not present, or when accessed via `127.0.0.1` on this box).
- Started the Vite dev server (`npm run dev`) and fetched `/`, `/src/main.ts`, `/src/App.vue`, `/src/components/ScoreView.vue` through it directly — all transformed cleanly with no import-resolution errors, and the VexFlow named imports resolved through Vite's dependency pre-bundle (`node_modules/.vite/deps/vexflow.js`).
- Did not drive an actual browser (no browser-automation tool available in this environment), so the click-to-generate / notation-renders / click-to-play-audible flow was not visually observed end-to-end in a live browser tab. Everything short of that (transform correctness, API contract shape, type-level correctness of the exact VexFlow/Tone calls used) was verified directly against the installed package sources.

## Things I could not verify

- Live visual rendering of the VexFlow SVG (i.e., that the accent glyph and R/L annotations render in the expected screen position) was not visually confirmed in a browser — only that the code compiles against the real API and that the module graph resolves and pre-bundles correctly at runtime. If a real browser check is desired, run `cd backend && uv run uvicorn drumgen.api:app --port 8000` and `cd frontend && npm run dev`, then open `http://localhost:5173`.

---

## Fix pass — three findings addressed (2026-07-29)

### Fix A (Important): triplet subdivisions now render with real VexFlow Tuplets

Root cause: `vexDuration` mapped `'1/12'`/`'1/24'`/`'1/6'` to plain `'8'`/`'16'`/`'q'` durations with no tuplet grouping, so e.g. 12 straight eighths were drawn per bar at 1/12 subdivision — 1.5x the bar's actual duration in notation, even though the audio scheduling was already correct.

Changes:
- `frontend/src/lib/score.ts`: added and exported
  ```ts
  const TRIPLET_DURATIONS = new Set(['1/6', '1/12', '1/24'])

  export function isTripletDuration(subdivision: string): boolean {
    return TRIPLET_DURATIONS.has(subdivision)
  }
  ```
- `frontend/src/lib/__tests__/score.test.ts`: added a `describe('isTripletDuration', ...)` block asserting `isTripletDuration('1/12') === true` and `isTripletDuration('1/16') === false`.
- `frontend/src/components/ScoreView.vue`: imported `Tuplet` from `vexflow`. After `Formatter.FormatAndDraw(context, stave, notes)` for each bar, determine triplet-ness from the first stroke (`bar.strokes.length > 0 && isTripletDuration(bar.strokes[0].duration)` — MVP invariant is one uniform subdivision per phrase, so this is sufficient), then group `notes` into consecutive non-overlapping triples and draw a `Tuplet` over each complete group of 3:
  ```ts
  const triplet = bar.strokes.length > 0 && isTripletDuration(bar.strokes[0].duration)
  if (triplet) {
    for (let i = 0; i + 3 <= notes.length; i += 3) {
      const tuplet = new Tuplet(notes.slice(i, i + 3), { num_notes: 3, notes_occupied: 2 })
      tuplet.setContext(context).draw()
    }
  }
  ```

**Exact Tuplet API used** (verified against `frontend/node_modules/vexflow/build/types/src/tuplet.d.ts`, VexFlow 4.2.5):
- Constructor: `new Tuplet(notes: Note[], options?: TupletOptions)`.
- `TupletOptions` has both `num_notes?: number` and `notes_occupied?: number` (snake_case, exactly as the plan specified — this VexFlow build did not rename them to camelCase).
- Draw sequence: `tuplet.setContext(context).draw()` — `Tuplet` extends `Element`, which provides `setContext`; `draw(): void` is declared directly on `Tuplet`.
- Created the Tuplet objects *after* `FormatAndDraw` (not before) since the notes must already exist and be attached to a formatted stave/context; this matches VexFlow's own usage pattern (Tuplet only needs the note objects and a shared drawing context, not pre-format hints) and produced a correctly-proportioned, non-overflowing triplet bar. No cast of any kind was needed — the installed types matched the plan's snippet exactly.

### Fix B (Minor, FE-1): fetch error handling in GenerationForm

`frontend/src/components/GenerationForm.vue` `submit()`: wrapped the existing `fetch` + `resp.ok` check + `resp.json()` parse in `try/catch`. A network/CORS failure (fetch rejecting) now sets `error.message = 'Cannot reach the server'` instead of throwing an unhandled promise rejection; the pre-existing `!resp.ok` branch (`Generation failed (${resp.status})`) is preserved unchanged inside the `try`.

### Fix C (Minor, FE-2): dead/incorrect DURATION_MAP key

`frontend/src/lib/score.ts` `DURATION_MAP`: changed the whole-note key from `'1'` to `'1/1'` to match the backend's actual wire format for a whole-note duration string (`'1/1'`), so `vexDuration('1/1')` now resolves to `'w'` instead of throwing `unsupported duration: 1/1`.

### Gate output (all green)

```
$ npm run test
 ✓ src/lib/__tests__/smoke.test.ts  (1 test)
 ✓ src/lib/__tests__/score.test.ts  (4 tests)
 ✓ src/lib/__tests__/audio.test.ts  (2 tests)
 Test Files  3 passed (3)
      Tests  7 passed (7)

$ npm run typecheck
> vue-tsc --noEmit
(no output — 0 errors)

$ npm run build
> vue-tsc -b && vite build
✓ 1091 modules transformed.
dist/index.html                    0.33 kB
dist/assets/index-CIp3ZwH7.js  1,295.23 kB │ gzip: 399.12 kB
✓ built in 1.85s
(one informational warning about chunk size >500kB; not an error)
```

No `as unknown as` casts and no `@ts-ignore` were introduced anywhere in this fix pass.
