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


def test_no_family_enabled_returns_422():
    resp = client.post(
        "/patterns2/generate",
        json=_body(singles=False, odd=False, paradiddle=False),
    )
    assert resp.status_code == 422
