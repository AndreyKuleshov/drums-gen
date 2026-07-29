from fractions import Fraction

from drumgen.catalog import FULL_CATALOG, MVP_CATALOG, RudimentTemplate
from drumgen.domain.models import Stroke
from drumgen.rules import find_violations


def _to_strokes(t: RudimentTemplate) -> list[Stroke]:
    return [Stroke(duration=Fraction(1, 16), hand=e.hand, accent=e.accent) for e in t.elements]


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
