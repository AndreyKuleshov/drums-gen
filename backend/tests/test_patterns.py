"""Tests for liking / listing / unliking patterns."""

import urllib.parse

from httpx import AsyncClient

Outbox = list[dict[str, str]]


def _stroke(hand: str, accent: bool = False) -> dict[str, object]:
    return {
        "duration": "1/4",
        "hand": hand,
        "accent": accent,
        "articulation": "normal",
        "surface": "snare",
        "grace": 0,
        "group": 0,
    }


# A valid 4/4 bar: four quarter notes summing to a whole bar.
_PHRASE = {
    "time_sig": {"num": 4, "den": 4},
    "tempo_bpm": 120,
    "subdivision": "1/16",
    "accent_mode": "rudiment",
    "bars": [
        {
            "time_sig": {"num": 4, "den": 4},
            "strokes": [
                _stroke("R", accent=True),
                _stroke("L"),
                _stroke("R"),
                _stroke("L"),
            ],
        }
    ],
}


def _token(box: Outbox, marker: str) -> str:
    for message in reversed(box):
        for line in message["text"].splitlines():
            if marker in line and "token=" in line:
                query = urllib.parse.urlparse(line.strip()).query
                return urllib.parse.parse_qs(query)["token"][0]
    raise AssertionError(f"no {marker} link found")


async def _signed_in(client: AsyncClient, outbox: Outbox, email: str = "liker@example.com") -> None:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Liker"},
    )
    await client.post("/auth/verify", json={"token": _token(outbox, "/verify")})


async def test_like_list_unlike(client: AsyncClient, outbox: Outbox) -> None:
    await _signed_in(client, outbox)

    liked = await client.post(
        "/patterns/like", json={"phrase": _PHRASE, "meta": {"bars": 1}, "title": "My groove"}
    )
    assert liked.status_code == 201
    pattern_id = liked.json()["id"]
    assert liked.json()["title"] == "My groove"

    listing = await client.get("/patterns/liked")
    assert listing.status_code == 200
    rows = listing.json()
    assert len(rows) == 1
    assert rows[0]["id"] == pattern_id
    assert rows[0]["phrase"]["tempo_bpm"] == 120

    removed = await client.delete(f"/patterns/liked/{pattern_id}")
    assert removed.status_code == 204
    assert (await client.get("/patterns/liked")).json() == []


async def test_like_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/patterns/like", json={"phrase": _PHRASE})
    assert resp.status_code == 401


async def test_cannot_unlike_others_pattern(client: AsyncClient, outbox: Outbox) -> None:
    await _signed_in(client, outbox, email="owner@example.com")
    liked = await client.post("/patterns/like", json={"phrase": _PHRASE})
    pattern_id = liked.json()["id"]
    await client.post("/auth/logout")

    # A different user must not be able to delete it.
    await _signed_in(client, outbox, email="intruder@example.com")
    resp = await client.delete(f"/patterns/liked/{pattern_id}")
    assert resp.status_code == 404


async def test_liked_list_is_per_user(client: AsyncClient, outbox: Outbox) -> None:
    await _signed_in(client, outbox, email="a@example.com")
    await client.post("/patterns/like", json={"phrase": _PHRASE})
    await client.post("/auth/logout")

    await _signed_in(client, outbox, email="b@example.com")
    assert (await client.get("/patterns/liked")).json() == []
