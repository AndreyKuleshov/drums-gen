from fastapi.testclient import TestClient

from drumgen.api import app

client = TestClient(app)


def test_generate_endpoint_returns_phrase():
    resp = client.post(
        "/generate",
        json={
            "time_sig": {"num": 4, "den": 4},
            "num_bars": 1,
            "min_subdivision": "1/16",
            "tempo_bpm": 100,
            "accent_mode": "rudiment",
            "seed": 1,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["bars"]) == 1
    assert body["bars"][0]["strokes"][0]["duration"] == "1/16"


def test_generate_endpoint_invalid_grid_returns_422():
    resp = client.post(
        "/generate",
        json={
            "time_sig": {"num": 3, "den": 8},
            "num_bars": 1,
            "min_subdivision": "1/5",
            "tempo_bpm": 100,
            "accent_mode": "rudiment",
        },
    )
    assert resp.status_code == 422


def test_generate_endpoint_nonpositive_subdivision_returns_422():
    resp = client.post(
        "/generate",
        json={
            "time_sig": {"num": 4, "den": 4},
            "num_bars": 1,
            "min_subdivision": "0/1",
            "tempo_bpm": 100,
            "accent_mode": "rudiment",
        },
    )
    assert resp.status_code == 422


def test_generate_endpoint_nonpositive_tempo_returns_422():
    resp = client.post(
        "/generate",
        json={
            "time_sig": {"num": 4, "den": 4},
            "num_bars": 1,
            "min_subdivision": "1/16",
            "tempo_bpm": 0,
            "accent_mode": "rudiment",
        },
    )
    assert resp.status_code == 422


def test_rudiments_endpoint():
    resp = client.get("/rudiments")
    assert resp.status_code == 200
    ids = {r["id"] for r in resp.json()}
    assert "single" in ids
    assert "single-paradiddle" in ids
