from pydantic import BaseModel

from drumgen.domain.enums import Difficulty, Hand


class RudimentElement(BaseModel):
    hand: Hand
    accent: bool = False
    weight: int = 1
    """Relative duration of this stroke, in base-grid units. 1 for a plain grid
    note; larger for the longer release notes of authentic rudiment rhythms
    (e.g. the accented tap that ends a roll)."""
    grace: int = 0
    """Grace notes ornamenting this stroke: 0 = none, 1 = flam, 2 = drag."""


class RudimentTemplate(BaseModel):
    id: str
    name: str
    elements: list[RudimentElement]
    mvp: bool
    violates_core_rules: bool
    difficulty: Difficulty = Difficulty.MID

    @property
    def length_cells(self) -> int:
        return len(self.elements)

    @property
    def total_weight(self) -> int:
        return sum(e.weight for e in self.elements)

    def mirrored(self) -> "RudimentTemplate":
        return RudimentTemplate(
            id=f"{self.id}-mirror",
            name=f"{self.name} (mirror)",
            elements=[
                RudimentElement(
                    hand=e.hand.other(), accent=e.accent, weight=e.weight, grace=e.grace
                )
                for e in self.elements
            ],
            mvp=self.mvp,
            violates_core_rules=self.violates_core_rules,
            difficulty=self.difficulty,
        )


def _elems(
    sticking: str,
    accents: set[int],
    weights: dict[int, int] | None = None,
    graces: dict[int, int] | None = None,
) -> list[RudimentElement]:
    weights = weights or {}
    graces = graces or {}
    return [
        RudimentElement(
            hand=Hand(ch),
            accent=(i in accents),
            weight=weights.get(i, 1),
            grace=graces.get(i, 0),
        )
        for i, ch in enumerate(sticking.replace(" ", ""))
    ]


MVP_CATALOG: list[RudimentTemplate] = [
    # --- Beginner: single/double strokes and the basic paradiddle ---
    RudimentTemplate(
        id="single",
        name="Single Stroke",
        elements=_elems("R", set()),
        mvp=True,
        violates_core_rules=False,
        difficulty=Difficulty.BEGINNER,
    ),
    RudimentTemplate(
        id="double",
        name="Double Stroke",
        elements=_elems("RR", {0}),
        mvp=True,
        violates_core_rules=False,
        difficulty=Difficulty.BEGINNER,
    ),
    RudimentTemplate(
        id="single-paradiddle",
        name="Single Paradiddle",
        elements=_elems("RLRR", {0}),
        mvp=True,
        violates_core_rules=False,
        difficulty=Difficulty.BEGINNER,
    ),
    # --- Mid: longer paradiddles and rolls ---
    RudimentTemplate(
        id="double-paradiddle",
        name="Double Paradiddle",
        elements=_elems("RLRLRR", {0}),
        mvp=True,
        violates_core_rules=False,
        difficulty=Difficulty.MID,
    ),
    RudimentTemplate(
        id="triple-paradiddle",
        name="Triple Paradiddle",
        elements=_elems("RLRLRLRR", {0}),
        mvp=True,
        violates_core_rules=False,
        difficulty=Difficulty.MID,
    ),
    RudimentTemplate(
        id="paradiddle-diddle",
        name="Paradiddle-diddle",
        elements=_elems("RLRRLL", {0}),
        mvp=True,
        violates_core_rules=False,
        difficulty=Difficulty.MID,
    ),
    RudimentTemplate(
        # Authentic rhythm: four diddle notes, then a longer accented release.
        id="five-stroke-roll",
        name="Five Stroke Roll",
        elements=_elems("RRLLR", {4}, weights={4: 2}),
        mvp=True,
        violates_core_rules=False,
        difficulty=Difficulty.MID,
    ),
    RudimentTemplate(
        id="seven-stroke-roll",
        name="Seven Stroke Roll",
        elements=_elems("RRLLRRL", {6}, weights={6: 2}),
        mvp=True,
        violates_core_rules=False,
        difficulty=Difficulty.MID,
    ),
    # --- Pro: flam and drag rudiments (ornamented with grace notes) ---
    RudimentTemplate(
        id="flam-accent",
        name="Flam Accent",
        elements=_elems("RLR", {0}, graces={0: 1}),
        mvp=True,
        violates_core_rules=False,
        difficulty=Difficulty.PRO,
    ),
    RudimentTemplate(
        id="flam-tap",
        name="Flam Tap",
        elements=_elems("RRLL", {0, 2}, graces={0: 1, 2: 1}),
        mvp=True,
        violates_core_rules=False,
        difficulty=Difficulty.PRO,
    ),
    RudimentTemplate(
        id="drag-tap",
        name="Drag Tap",
        elements=_elems("RL", {0}, graces={0: 2}),
        mvp=True,
        violates_core_rules=False,
        difficulty=Difficulty.PRO,
    ),
]

FULL_CATALOG: list[RudimentTemplate] = [
    *MVP_CATALOG,
    RudimentTemplate(
        id="triple-stroke",
        name="Triple Stroke",
        elements=_elems("RRR", {0}),
        mvp=False,
        violates_core_rules=True,
    ),
]
