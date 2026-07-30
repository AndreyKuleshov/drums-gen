from pydantic import BaseModel

from drumgen.domain.enums import Hand


class RudimentElement(BaseModel):
    hand: Hand
    accent: bool = False
    weight: int = 1
    """Relative duration of this stroke, in base-grid units. 1 for a plain grid
    note; larger for the longer release notes of authentic rudiment rhythms
    (e.g. the accented tap that ends a roll)."""


class RudimentTemplate(BaseModel):
    id: str
    name: str
    elements: list[RudimentElement]
    mvp: bool
    violates_core_rules: bool

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
                RudimentElement(hand=e.hand.other(), accent=e.accent, weight=e.weight)
                for e in self.elements
            ],
            mvp=self.mvp,
            violates_core_rules=self.violates_core_rules,
        )


def _elems(
    sticking: str, accents: set[int], weights: dict[int, int] | None = None
) -> list[RudimentElement]:
    weights = weights or {}
    return [
        RudimentElement(hand=Hand(ch), accent=(i in accents), weight=weights.get(i, 1))
        for i, ch in enumerate(sticking.replace(" ", ""))
    ]


MVP_CATALOG: list[RudimentTemplate] = [
    RudimentTemplate(
        id="single",
        name="Single Stroke",
        elements=_elems("R", set()),
        mvp=True,
        violates_core_rules=False,
    ),
    RudimentTemplate(
        id="double",
        name="Double Stroke",
        elements=_elems("RR", {0}),
        mvp=True,
        violates_core_rules=False,
    ),
    RudimentTemplate(
        id="single-paradiddle",
        name="Single Paradiddle",
        elements=_elems("RLRR", {0}),
        mvp=True,
        violates_core_rules=False,
    ),
    RudimentTemplate(
        id="double-paradiddle",
        name="Double Paradiddle",
        elements=_elems("RLRLRR", {0}),
        mvp=True,
        violates_core_rules=False,
    ),
    RudimentTemplate(
        id="triple-paradiddle",
        name="Triple Paradiddle",
        elements=_elems("RLRLRLRR", {0}),
        mvp=True,
        violates_core_rules=False,
    ),
    RudimentTemplate(
        id="paradiddle-diddle",
        name="Paradiddle-diddle",
        elements=_elems("RLRRLL", {0}),
        mvp=True,
        violates_core_rules=False,
    ),
    RudimentTemplate(
        # Authentic rhythm: four diddle notes, then a longer accented release.
        id="five-stroke-roll",
        name="Five Stroke Roll",
        elements=_elems("RRLLR", {4}, weights={4: 2}),
        mvp=True,
        violates_core_rules=False,
    ),
    RudimentTemplate(
        id="seven-stroke-roll",
        name="Seven Stroke Roll",
        elements=_elems("RRLLRRL", {6}, weights={6: 2}),
        mvp=True,
        violates_core_rules=False,
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
