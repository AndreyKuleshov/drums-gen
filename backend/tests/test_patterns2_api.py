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


def test_no_family_enabled_returns_422():
    resp = client.post(
        "/patterns2/generate",
        json=_body(singles=False, odd=False, paradiddle=False),
    )
    assert resp.status_code == 422
