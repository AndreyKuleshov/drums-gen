from drumgen.domain.enums import AccentMode, Articulation, Hand, Surface


def test_enum_values():
    assert Hand.R.value == "R"
    assert Hand.L.value == "L"
    assert Articulation.NORMAL.value == "normal"
    assert Surface.SNARE.value == "snare"
    assert {m.value for m in AccentMode} == {"rudiment", "metric", "both"}
