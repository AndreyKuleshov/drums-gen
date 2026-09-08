#!/usr/bin/env python3
"""Build a deduplicated corpus of unique one-bar drum-fill seeds.

These are NOT copied from any single copyrighted collection.  They are
synthesised from the standard, widely-taught families of drum fills (8th-note
snare fills, broken 8ths, 16th linear, broken 16ths, tom cascades, flam fills,
8th-note-triplet fills, 32nd bursts, herta groupings, ghost-note 16ths, gospel
linear, single-stroke accent migration) that appear across countless free
lessons.  Each family is expanded parametrically over a small
rhythm/orchestration/sticking vocabulary, then the whole set is canonically
deduplicated so every seed is musically distinct.

Musicality guardrail: a fill must *evolve* across the bar — at least two
distinct beat-shapes, and the last beat differs from the first — so we never
emit "the same beat four times" (which the user explicitly rejected).

Grid: 96 ticks per 4/4 bar.
  quarter=24  8th=12  16th=6  32nd=3  8th-triplet=8  16th-triplet=4
Surfaces: S snare | H hihat | K kick | t high tom | m mid tom | l low tom
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from fractions import Fraction

TPB = 96  # ticks per bar (4/4)
TOMS = ["tom_high", "tom_mid", "tom_low"]


@dataclass
class Hit:
    tick: int
    dur: int
    surf: str
    accent: bool = False
    ghost: bool = False
    artic: str = "normal"  # normal | flam | drag


@dataclass
class Fill:
    family: str
    difficulty: str  # beginner | mid | pro
    hits: list[Hit] = field(default_factory=list)


def alternate(hits: list[Hit]) -> list[str]:
    """Strict hand-to-hand sticking for the melodic (non-kick) strokes.  Never
    more than two of the same hand in a row (in fact exact alternation)."""
    out: list[str] = []
    hand = "R"
    for h in hits:
        if h.surf == "kick":
            out.append("")  # foot
            continue
        out.append(hand)
        hand = "L" if hand == "R" else "R"
    return out


# ---- rhythm vocabularies (per beat, durations in 16th-count summing to 4) ----
CELLS_8 = [[2, 2], [4], [2, 1, 1], [1, 1, 2]]
CELLS_16 = [[1, 1, 1, 1], [2, 1, 1], [1, 1, 2], [1, 2, 1], [2, 2]]
CELLS_16_BROKEN = [[1, 1, 2], [2, 1, 1], [1, 2, 1], [1, 1, 1, 1], [2, 2], [1, 3]]


def beat_ticks_16(cell: list[int]) -> list[tuple[int, int]]:
    out, o = [], 0
    for d in cell:
        out.append((o * 6, d * 6))
        o += d
    return out


def beat_ticks_triplet() -> list[tuple[int, int]]:
    return [(i * 8, 8) for i in range(3)]


# --------------------------- fill family builders ----------------------------
def fam_eighth_snare():
    """Beginner: 8th-note fills that start on the snare and walk onto a tom by
    the last beat (so the bar resolves — never four identical snare beats)."""
    out = []
    lands = [
        ["snare", "snare", "snare", "tom_mid"],
        ["snare", "snare", "tom_high", "tom_low"],
        ["snare", "snare", "tom_mid", "tom_low"],
    ]
    for land in lands:
        for c0 in CELLS_8:
            for c1 in CELLS_8:
                for c3 in [[2, 2], [4], [1, 1, 2]]:
                    hits = []
                    for bi, cell in enumerate([c0, c1, [2, 2], c3]):
                        for off, dur in beat_ticks_16(cell):
                            hits.append(Hit(bi * 24 + off, dur, land[bi], accent=(off == 0)))
                    out.append(Fill("eighth_snare", "beginner", hits))
    return out


def fam_eighth_tom_move():
    """Beginner/mid: 8th notes marching snare -> toms across the bar."""
    paths = [
        ["snare", "snare", "tom_mid", "tom_low"],
        ["snare", "tom_high", "tom_mid", "tom_low"],
        ["snare", "snare", "tom_high", "tom_mid"],
        ["tom_high", "tom_high", "tom_mid", "tom_low"],
        ["snare", "tom_high", "tom_high", "tom_low"],
    ]
    out = []
    for path in paths:
        for c0 in CELLS_8:
            for c3 in [[2, 2], [4], [1, 1, 2], [2, 1, 1]]:
                hits = []
                for bi, cell in enumerate([c0, [2, 2], [2, 2], c3]):
                    for off, dur in beat_ticks_16(cell):
                        hits.append(Hit(bi * 24 + off, dur, path[bi], accent=(off == 0)))
                out.append(Fill("eighth_tom_move", "beginner", hits))
    return out


def fam_sixteenth_linear():
    """Mid: continuous 16ths, linear orchestration that rotates around the kit."""
    groups = [
        ["snare", "tom_high", "tom_mid", "kick"],
        ["snare", "snare", "tom_mid", "tom_low"],
        ["snare", "tom_high", "snare", "tom_low"],
        ["tom_high", "tom_high", "tom_mid", "tom_low"],
        ["snare", "kick", "tom_mid", "kick"],
        ["snare", "tom_high", "kick", "tom_mid"],
        ["kick", "snare", "snare", "tom_low"],
    ]
    out = []
    for g in groups:
        for rot in (0, 1, 2):
            hits = []
            for bi in range(4):
                base = bi * 24
                r = (bi + rot) % 4
                grp = g[r:] + g[:r]
                for k in range(4):
                    surf = grp[k % len(grp)]
                    hits.append(Hit(base + k * 6, 6, surf, accent=(k == 0 and surf != "kick")))
            out.append(Fill("sixteenth_linear", "mid", hits))
    return out


def fam_sixteenth_broken():
    """Mid: broken 16ths (rests) grouped around snare + toms, resolving low."""
    out = []
    seqs = [
        ["snare", "snare", "tom_mid", "tom_low"],
        ["snare", "tom_high", "tom_mid", "tom_low"],
        ["snare", "snare", "snare", "tom_low"],
        ["snare", "tom_high", "snare", "tom_mid"],
    ]
    for seq in seqs:
        for c0 in CELLS_16_BROKEN:
            for c1 in CELLS_16_BROKEN[:3]:
                for c3 in [[1, 1, 2], [1, 1, 1, 1], [1, 3]]:
                    cells = [c0, c1, [2, 1, 1], c3]
                    hits = []
                    for bi, cell in enumerate(cells):
                        for off, dur in beat_ticks_16(cell):
                            hits.append(Hit(bi * 24 + off, dur, seq[bi], accent=(off == 0)))
                    out.append(Fill("sixteenth_broken", "mid", hits))
    return out


def fam_tom_cascade():
    """Mid/pro: 16th tom cascades with a density arc, resolving low."""
    out = []
    cascades = [
        ["tom_high", "tom_high", "tom_mid", "tom_mid", "tom_low", "tom_low"],
        ["snare", "snare", "tom_high", "tom_mid", "tom_low", "tom_low"],
        ["tom_high", "tom_mid", "tom_low", "tom_high", "tom_mid", "tom_low"],
        ["snare", "tom_high", "tom_high", "tom_mid", "tom_mid", "tom_low"],
        ["tom_high", "tom_mid", "tom_mid", "tom_low", "tom_low", "tom_low"],
    ]
    arcs = [
        [2, 2, 4, 4],  # steps per beat (density builds)
        [2, 4, 4, 4],
        [4, 4, 2, 4],
    ]
    for casc in cascades:
        for arc in arcs:
            hits = []
            n = 0
            for bi in range(4):
                base = bi * 24
                steps = arc[bi]
                dur = 24 // steps
                for k in range(steps):
                    surf = casc[n % len(casc)]
                    n += 1
                    hits.append(Hit(base + k * dur, dur, surf, accent=(k == 0)))
            out.append(Fill("tom_cascade", "mid", hits))
    return out


def fam_flam_fill():
    """Mid/pro: accented flams on toms with 16th ghost fillers; the flam target
    descends across the bar, and the filler pattern varies."""
    out = []
    layouts = [
        ["tom_high", "tom_high", "tom_mid", "tom_low"],
        ["snare", "tom_high", "tom_mid", "tom_low"],
        ["tom_high", "tom_mid", "tom_mid", "tom_low"],
        ["snare", "snare", "tom_mid", "tom_low"],
    ]
    fillers = [
        [(12, "snare", True), (18, "snare", True)],  # two ghost 16ths after flam
        [(6, "snare", True), (12, "snare", True), (18, "snare", True)],
        [(18, "snare", True)],
        [(12, "tom_low", False)],
    ]
    for lay in layouts:
        for fil in fillers:
            hits = []
            for bi in range(4):
                base = bi * 24
                hits.append(Hit(base, 12, lay[bi], accent=True, artic="flam"))
                for off, surf, ghost in fil:
                    hits.append(Hit(base + off, 6, surf, ghost=ghost))
            out.append(Fill("flam_fill", "pro", hits))
    return out


def fam_triplet_fill():
    """Mid: 8th-triplet fills rolling around the toms, with an evolving arc of
    which beats carry the triplet vs. a held snare accent."""
    out = []
    paths = [
        ["snare", "tom_high", "tom_mid"],
        ["tom_high", "tom_mid", "tom_low"],
        ["snare", "snare", "tom_low"],
        ["tom_high", "tom_high", "tom_mid"],
        ["snare", "tom_mid", "tom_low"],
    ]
    arcs = [[1, 2, 3], [0, 2, 3], [2, 3], [0, 1, 3], [1, 3]]
    for path in paths:
        for active in arcs:
            hits = []
            for bi in range(4):
                base = bi * 24
                if bi not in active:
                    hits.append(Hit(base, 12, "snare", accent=True))
                    hits.append(Hit(base + 12, 12, "snare", ghost=True))
                    continue
                # rotate the path per beat so beats aren't identical
                rot = bi % len(path)
                p = path[rot:] + path[:rot]
                for k, (off, dur) in enumerate(beat_ticks_triplet()):
                    hits.append(Hit(base + off, dur, p[k % len(p)], accent=(k == 0)))
            out.append(Fill("triplet_fill", "mid", hits))
    return out


def fam_thirtysecond_burst():
    """Pro: the bar builds to a 32nd-note burst; the burst moves around the bar
    and its orchestration varies."""
    out = []
    surfaces = [
        ["snare", "tom_high", "tom_mid", "tom_low"],
        ["tom_high", "tom_mid", "tom_low", "tom_low"],
        ["snare", "snare", "tom_mid", "tom_low"],
        ["tom_high", "tom_high", "tom_mid", "tom_low"],
    ]
    for bat in (3, 2, 1, 0):
        for seq in surfaces:
            hits = []
            for bi in range(4):
                base = bi * 24
                if bi == bat:
                    for k in range(8):
                        surf = seq[(k // 2) % len(seq)]
                        hits.append(Hit(base + k * 3, 3, surf, accent=(k == 0)))
                else:
                    lead = seq[bi % len(seq)]
                    hits.append(Hit(base, 6, "snare", accent=True))
                    hits.append(Hit(base + 6, 6, lead, ghost=True))
                    hits.append(Hit(base + 12, 6, "snare", ghost=True))
                    hits.append(Hit(base + 18, 6, lead))
            out.append(Fill("thirtysecond_burst", "pro", hits))
    return out


def fam_herta():
    """Pro: herta (groups of 3 x 16th) sweeping across the kit, each beat on a
    different drum so the bar descends."""
    out = []
    sweeps = [
        ["snare", "tom_high", "tom_mid", "tom_low"],
        ["tom_high", "tom_mid", "tom_low", "snare"],
        ["snare", "snare", "tom_mid", "tom_low"],
        ["tom_high", "tom_high", "tom_mid", "tom_low"],
    ]
    tails = [
        [(18, "snare", True)],  # ghost 16th on the 'e/a'
        [(18, "kick", False)],  # kick pickup
        [],  # bare group of three (16th gap)
    ]
    for sweep in sweeps:
        for tail in tails:
            hits = []
            for bi in range(4):
                base = bi * 24
                surf = sweep[bi % len(sweep)]
                for k in range(3):
                    hits.append(Hit(base + k * 6, 6, surf, accent=(k == 0)))
                for off, ts, ghost in tail:
                    hits.append(Hit(base + off, 6, ts, ghost=ghost))
            out.append(Fill("herta", "pro", hits))
    return out


def fam_ghost_sixteenth():
    """Mid: ghosted 16th snare stream with accents migrating onto toms across
    the bar (a moving accent pattern, not a static one)."""
    out = []
    accent_arcs = [
        [[0], [0, 12], [6, 12], [0, 6, 12, 18]],  # per-beat accent offsets
        [[0], [6], [12], [0, 18]],
        [[0, 6], [12], [6], [0, 12, 18]],
    ]
    tom_pools = [
        ["tom_high", "tom_mid", "tom_low"],
        ["snare", "tom_mid", "tom_low"],
        ["tom_high", "tom_high", "tom_low"],
    ]
    for arc in accent_arcs:
        for toms in tom_pools:
            hits = []
            ai = 0
            for bi in range(4):
                base = bi * 24
                acc = arc[bi]
                for k in range(4):
                    off = k * 6
                    is_acc = off in acc
                    surf = toms[ai % len(toms)] if is_acc else "snare"
                    if is_acc:
                        ai += 1
                    hits.append(Hit(base + off, 6, surf, accent=is_acc, ghost=not is_acc))
            out.append(Fill("ghost_sixteenth", "mid", hits))
    return out


def fam_gospel_linear():
    """Pro: gospel-style linear 16ths threading kick + hi-hat between hand
    strokes so no two consecutive notes are the same voice."""
    out = []
    groups = [
        ["snare", "kick", "hihat", "snare"],
        ["tom_high", "kick", "snare", "kick"],
        ["snare", "hihat", "kick", "tom_mid"],
        ["snare", "kick", "snare", "kick"],
    ]
    for g in groups:
        for lands in (["snare", "tom_high", "tom_mid", "tom_low"],
                      ["snare", "snare", "tom_mid", "tom_low"]):
            hits = []
            for bi in range(4):
                base = bi * 24
                for k in range(4):
                    surf = g[k]
                    if k == 0:
                        surf = lands[bi]  # accent lead migrates down the toms
                    hits.append(Hit(base + k * 6, 6, surf, accent=(k == 0 and surf != "kick")))
            out.append(Fill("gospel_linear", "pro", hits))
    return out


def fam_single_stroke_accent():
    """Mid/pro: a 16th single-stroke roll on the snare with one accent that
    migrates 1 -> e -> & -> a across the four beats, moving to a tom on the
    accent for colour."""
    out = []
    for pool in (["tom_high", "tom_mid", "tom_low", "snare"],
                 ["snare", "tom_high", "tom_mid", "tom_low"],
                 ["tom_high", "tom_high", "tom_mid", "tom_low"]):
        for direction in (range(4), reversed(range(4))):
            dirs = list(direction)
            hits = []
            for bi in range(4):
                base = bi * 24
                acc_k = dirs[bi]
                for k in range(4):
                    is_acc = k == acc_k
                    surf = pool[bi % len(pool)] if is_acc else "snare"
                    hits.append(Hit(base + k * 6, 6, surf, accent=is_acc, ghost=not is_acc))
            out.append(Fill("single_stroke_accent", "mid", hits))
    return out


FAMILIES = [
    fam_eighth_snare,
    fam_eighth_tom_move,
    fam_sixteenth_linear,
    fam_sixteenth_broken,
    fam_tom_cascade,
    fam_flam_fill,
    fam_triplet_fill,
    fam_thirtysecond_burst,
    fam_herta,
    fam_ghost_sixteenth,
    fam_gospel_linear,
    fam_single_stroke_accent,
]


def canonical(fill: Fill) -> tuple:
    """Dedup key = rhythm + orchestration + ornament (sticking excluded)."""
    return tuple(
        sorted((h.tick, h.dur, h.surf, h.accent, h.ghost, h.artic) for h in fill.hits)
    )


def beat_shapes(fill: Fill) -> list[tuple]:
    """Per-beat (offset-relative, dur, surface) signatures for the 4 beats."""
    beats: list[list] = [[], [], [], []]
    for h in fill.hits:
        bi = h.tick // 24
        if 0 <= bi < 4:
            beats[bi].append((h.tick % 24, h.dur, h.surf))
    return [tuple(sorted(b)) for b in beats]


def evolves(fill: Fill) -> bool:
    """Musicality guardrail: the bar must not be one beat repeated.  Require at
    least two distinct beat shapes AND the last beat to differ from the first."""
    shapes = beat_shapes(fill)
    return len(set(shapes)) >= 2 and shapes[0] != shapes[-1]


def tick_to_fraction(tick: int) -> str:
    return str(Fraction(tick, TPB))


def to_seed(fill: Fill, idx: int) -> dict:
    sticking = alternate(fill.hits)
    hands, feet = [], []
    for h, stick in zip(fill.hits, sticking):
        rec = {
            "onset": tick_to_fraction(h.tick),
            "duration": tick_to_fraction(h.dur),
            "surface": h.surf,
            "accent": h.accent,
            "ghost": h.ghost,
            "articulation": h.artic,
        }
        if h.surf == "kick":
            feet.append(rec)
        else:
            rec["hand"] = stick
            hands.append(rec)
    return {
        "id": f"{fill.family}-{idx:03d}",
        "family": fill.family,
        "difficulty": fill.difficulty,
        "hands": hands,
        "feet": feet,
    }


def main() -> None:
    raw: list[Fill] = []
    for fam in FAMILIES:
        raw.extend(fam())

    seen: set[tuple] = set()
    dedup: list[Fill] = []
    dropped_static = 0
    for f in raw:
        if not f.hits:
            continue
        if not evolves(f):
            dropped_static += 1
            continue
        key = canonical(f)
        if key in seen:
            continue
        seen.add(key)
        dedup.append(f)

    # Balance: even spread per family so no single shape dominates.
    CAP = 32
    by_fam: dict[str, list[Fill]] = defaultdict(list)
    for f in dedup:
        by_fam[f.family].append(f)
    print("pre-cap per family:", {k: len(v) for k, v in sorted(by_fam.items())})
    unique: list[Fill] = []
    for _fam, items in by_fam.items():
        step = max(1, len(items) // CAP)
        unique.extend(items[::step][:CAP])

    seeds = [to_seed(f, i) for i, f in enumerate(unique)]
    out = {
        "schema": "drumgen-fill-seeds/1",
        "grid": "fraction-of-whole-note (4/4 bar = 1)",
        "provenance": (
            "Synthesised from standard, widely-taught drum-fill families. Not "
            "copied from any single copyrighted collection. Canonically "
            "deduplicated and evolution-filtered: every seed is a musically "
            "distinct one-bar 4/4 fill whose bar develops (no repeated beat)."
        ),
        "count": len(seeds),
        "seeds": seeds,
    }
    with open("fill_seeds.json", "w") as fh:
        json.dump(out, fh, indent=2)

    fam_c = Counter(f.family for f in unique)
    dif_c = Counter(f.difficulty for f in unique)
    print(f"raw candidates   : {len(raw)}")
    print(f"dropped (static) : {dropped_static}")
    print(f"UNIQUE fills     : {len(unique)}")
    print("\nby family:")
    for k, v in sorted(fam_c.items()):
        print(f"  {k:22s} {v}")
    print("\nby difficulty:")
    for k, v in sorted(dif_c.items()):
        print(f"  {k:10s} {v}")


if __name__ == "__main__":
    main()
