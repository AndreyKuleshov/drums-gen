from drumgen.domain.enums import Hand
from drumgen.domain.models import Stroke


def test_stroke_ghost_defaults_false():
    s = Stroke(duration="1/16", hand=Hand.R)
    assert s.ghost is False


def test_stroke_ghost_can_be_set():
    s = Stroke(duration="1/16", hand=Hand.L, ghost=True)
    assert s.ghost is True
