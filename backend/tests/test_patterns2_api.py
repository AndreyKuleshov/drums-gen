from fastapi.testclient import TestClient

from drumgen.api import app

client = TestClient(app)


def _body(**kw: object) -> dict[str, object]:
    base: dict[str, object] = {
        "time_sig": {"num": 4, "den": 4},
        "num_bars": 2,
        "subdivision": "1/16",
        "tempo_bpm": 110,
    }
    base.update(kw)
    return base


def test_generate_returns_a_phrase():
    resp = client.post("/patterns2/generate", json=_body(seed=1))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["bars"]) == 2
    assert len(data["bars"][0]["strokes"]) == 16
    # ghost field is present on strokes
    assert "ghost" in data["bars"][0]["strokes"][0]


def test_kit_voicing_returns_a_groove():
    resp = client.post("/patterns2/generate", json=_body(seed=1, voicing="kit"))
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["bars"]) == 2
    bar = data["bars"][0]
    # Groove shape: polyphonic hands + feet voices (not a monophonic Phrase)
    assert "hands" in bar
    assert "feet" in bar
    assert any(f["surface"] == "kick" for f in bar["feet"])
    surfaces = {h["surface"] for b in data["bars"] for h in b["hands"]}
    assert "hihat" in surfaces


def test_linear_voicing_returns_a_groove_with_no_simultaneous_strokes():
    resp = client.post("/patterns2/generate", json=_body(seed=1, voicing="linear"))
    assert resp.status_code == 200
    data = resp.json()
    for bar in data["bars"]:
        hand_onsets = {h["onset"] for h in bar["hands"]}
        foot_onsets = {f["onset"] for f in bar["feet"]}
        assert not (hand_onsets & foot_onsets)  # linear: one stroke at a time


def test_mixed_durations_returns_both_note_values():
    resp = client.post("/patterns2/generate", json=_body(seed=1, mixed=True))
    assert resp.status_code == 200
    data = resp.json()
    durs = {s["duration"] for bar in data["bars"] for s in bar["strokes"]}
    assert "1/8" in durs
    assert "1/16" in durs


def test_no_family_enabled_returns_422():
    resp = client.post(
        "/patterns2/generate",
        json=_body(singles=False, odd=False, paradiddle=False),
    )
    assert resp.status_code == 422
