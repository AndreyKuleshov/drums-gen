from drumgen.sticking_generator import VOCAB, mirror, rules_hold


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
