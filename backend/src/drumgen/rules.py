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
