"""Tests for pattern rating capture + admin review/moderation."""

import urllib.parse

from httpx import AsyncClient

Outbox = list[dict[str, str]]


def _token(box: Outbox, marker: str) -> str:
    for message in reversed(box):
        for line in message["text"].splitlines():
            if marker in line and "token=" in line:
                query = urllib.parse.urlparse(line.strip()).query
                return urllib.parse.parse_qs(query)["token"][0]
    raise AssertionError(f"no {marker} link found")


async def _signed_in(client: AsyncClient, outbox: Outbox, email: str) -> None:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": "Rater"},
    )
    await client.post("/auth/verify", json={"token": _token(outbox, "/verify")})


async def test_userout_exposes_is_admin(client: AsyncClient, outbox: Outbox) -> None:
    await _signed_in(client, outbox, "plain@example.com")
    me = await client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["is_admin"] is False


def test_content_hash_is_stable_and_order_independent() -> None:
    from drumgen.ratings.service import content_hash

    a = {"tempo_bpm": 120, "bars": [{"strokes": [1, 2]}], "subdivision": "1/16"}
    b = {"subdivision": "1/16", "bars": [{"strokes": [1, 2]}], "tempo_bpm": 120}
    c = {"tempo_bpm": 121, "bars": [{"strokes": [1, 2]}], "subdivision": "1/16"}
    ha, hb, hc = content_hash(a), content_hash(b), content_hash(c)
    assert ha == hb  # key order does not change the hash
    assert ha != hc  # different content → different hash
    assert len(ha) == 64
