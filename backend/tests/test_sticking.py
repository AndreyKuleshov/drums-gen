from fractions import Fraction

import pytest

from drumgen.domain.models import Phrase, TimeSignature
from drumgen.generator import GenerationError
from drumgen.sticking_generator import VOCAB, StickingRequest, generate_sticking, mirror, rules_hold


def test_vocab_has_three_families_with_expected_lengths():
    assert set(VOCAB) == {"singles", "odd", "paradiddle"}
    lengths = {fam: sorted(len(b) for b in blocks) for fam, blocks in VOCAB.items()}
    assert lengths["singles"] == [1, 2, 3, 4]
    assert lengths["odd"] == [3, 5, 7]
    assert lengths["paradiddle"] == [4, 6, 6]


def test_every_canonical_block_is_individually_legal():
    for blocks in VOCAB.values():
        for block in blocks:
            assert rules_hold(block), block


def test_mirror_swaps_hands_and_preserves_accents():
    block = VOCAB["odd"][0]  # Rll -> (('R',True),('L',False),('L',False))
    assert mirror(block) == (("L", True), ("R", False), ("R", False))
    # Mirrors are also legal.
    for blocks in VOCAB.values():
        for block in blocks:
            assert rules_hold(mirror(block))


def test_rule1_adjacent_accents_must_alternate():
    # two adjacent accents, same hand -> illegal
    assert not rules_hold(((("R", True)), ("R", True)))
    # adjacent accents, different hands -> legal
    assert rules_hold((("R", True), ("L", True)))
    # two same-hand accents split by a ghost -> legal (RlR...)
    assert rules_hold((("R", True), ("L", False), ("R", True)))


def test_rule2_no_more_than_two_ghosts_per_hand_in_a_row():
    assert rules_hold((("R", True), ("L", False), ("L", False)))  # 2 ghosts ok
    assert not rules_hold((("R", True), ("L", False), ("L", False), ("L", False)))  # 3 ghosts
    # ghost hand change resets the run
    assert rules_hold((("L", False), ("L", False), ("R", False), ("R", False)))


def test_rule2_counts_accents_and_ghosts_together():
    # No three strokes on the same hand in a row, even mixing an accent with
    # ghosts — you can't physically play three in a row with one hand.
    assert not rules_hold((("L", False), ("L", False), ("L", True)))  # l l L (seam bug)
    assert not rules_hold((("L", True), ("L", False), ("L", False)))  # L l l
    assert not rules_hold((("R", True), ("R", False), ("R", False)))  # R r r
    # two same-hand strokes (accent + ghost, either order) stay legal
    assert rules_hold((("L", True), ("L", False)))
    assert rules_hold((("R", False), ("R", True), ("L", False)))


_44 = TimeSignature(num=4, den=4)


def _req(**kw: object) -> StickingRequest:
    base: dict[str, object] = {
        "time_sig": _44,
        "num_bars": 1,
        "subdivision": Fraction(1, 16),
        "tempo_bpm": 100,
    }
    base.update(kw)
    return StickingRequest.model_validate(base)


def _stream(phrase: Phrase) -> list[tuple[str, bool]]:
    return [(s.hand.value, s.accent) for bar in phrase.bars for s in bar.strokes]


def test_fills_exact_note_count_per_bar():
    phrase = generate_sticking(_req(num_bars=2, subdivision=Fraction(1, 16), seed=1))
    assert len(phrase.bars) == 2
    for bar in phrase.bars:
        assert len(bar.strokes) == 16  # 4/4 at 1/16
        assert all(s.duration == Fraction(1, 16) for s in bar.strokes)


def test_every_note_is_accent_xor_ghost():
    phrase = generate_sticking(_req(num_bars=4, seed=3))
    for bar in phrase.bars:
        for s in bar.strokes:
            assert s.accent != s.ghost  # exactly one is true


@pytest.mark.parametrize("seed", range(30))
def test_generated_phrase_always_satisfies_both_rules(seed: int):
    phrase = generate_sticking(_req(num_bars=4, subdivision=Fraction(1, 16), seed=seed))
    assert rules_hold(_stream(phrase))


def test_family_toggles_are_respected_singles_only():
    # Singles are all accents; with only singles enabled, no ghosts appear.
    phrase = generate_sticking(_req(num_bars=2, singles=True, odd=False, paradiddle=False, seed=5))
    assert all(s.accent and not s.ghost for bar in phrase.bars for s in bar.strokes)


def test_each_family_alone_can_fill_a_bar():
    for fam in ("singles", "odd", "paradiddle"):
        kw: dict[str, object] = {"singles": False, "odd": False, "paradiddle": False, fam: True}
        phrase = generate_sticking(_req(num_bars=1, subdivision=Fraction(1, 16), seed=2, **kw))
        assert len(phrase.bars[0].strokes) == 16


def test_deterministic_for_a_fixed_seed():
    a = generate_sticking(_req(num_bars=3, seed=42)).model_dump()
    b = generate_sticking(_req(num_bars=3, seed=42)).model_dump()
    assert a == b


def test_eighth_subdivision_uses_eight_notes_per_bar():
    phrase = generate_sticking(_req(num_bars=1, subdivision=Fraction(1, 8), seed=1))
    assert len(phrase.bars[0].strokes) == 8
    assert all(s.duration == Fraction(1, 8) for s in phrase.bars[0].strokes)


def test_no_family_enabled_raises():
    with pytest.raises(GenerationError):
        generate_sticking(_req(singles=False, odd=False, paradiddle=False))


def test_subdivision_that_does_not_divide_the_bar_raises():
    # 4/4 bar length 1; 1 / (3/8) = 8/3 is not a whole number of notes.
    with pytest.raises(GenerationError):
        generate_sticking(_req(subdivision=Fraction(3, 8)))


def test_pathological_request_raises_instead_of_crashing():
    # An unboundedly large phrase must be rejected with GenerationError, never an
    # uncaught RecursionError.
    with pytest.raises(GenerationError):
        generate_sticking(
            _req(time_sig=TimeSignature(num=1, den=1), subdivision=Fraction(1, 2500), num_bars=1)
        )


def test_large_supported_request_still_generates():
    # 64 bars of 4/4 at 1/16 = 1024 notes is exactly the supported ceiling.
    phrase = generate_sticking(_req(num_bars=64, subdivision=Fraction(1, 16), seed=1))
    assert len(phrase.bars) == 64
    assert sum(len(b.strokes) for b in phrase.bars) == 1024
