from fractions import Fraction

from drumgen.domain.enums import Hand
from drumgen.domain.models import Stroke
from drumgen.rules import find_violations, is_valid


def _s(hand: Hand, accent: bool = False) -> Stroke:
    return Stroke(duration=Fraction(1, 16), hand=hand, accent=accent)


def test_clean_sequence_has_no_violations():
    strokes = [_s(Hand.R), _s(Hand.L), _s(Hand.R), _s(Hand.L)]
    assert find_violations(strokes) == []
    assert is_valid(strokes) is True


def test_rule1_accent_after_unaccent_same_hand():
    # rR: unaccented R then accented R
    strokes = [_s(Hand.R, accent=False), _s(Hand.R, accent=True)]
    violations = find_violations(strokes)
    assert [v.rule for v in violations] == ["R1"]
    assert violations[0].index == 1


def test_rule1_allows_accent_after_unaccent_different_hand():
    strokes = [_s(Hand.R, accent=False), _s(Hand.L, accent=True)]
    assert find_violations(strokes) == []


def test_rule2_three_same_hand_in_a_row():
    strokes = [_s(Hand.R), _s(Hand.R), _s(Hand.R)]
    violations = find_violations(strokes)
    assert [v.rule for v in violations] == ["R2"]
    assert violations[0].index == 2


def test_two_same_hand_is_allowed():
    strokes = [_s(Hand.R), _s(Hand.R), _s(Hand.L)]
    assert find_violations(strokes) == []
