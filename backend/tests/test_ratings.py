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


async def test_pattern_ratings_table_exists(client: AsyncClient) -> None:
    # The `client` fixture runs create_all and overrides get_session; if the model
    # is registered on Base.metadata the table exists in the test DB.
    from sqlalchemy import text

    from drumgen.api import app
    from drumgen.db.base import SCHEMA
    from drumgen.db.engine import get_session

    override = app.dependency_overrides[get_session]
    agen = override()
    session = await agen.__anext__()
    try:
        count = await session.scalar(text(f'SELECT count(*) FROM {SCHEMA}."pattern_ratings"'))
        assert count == 0
    finally:
        await agen.aclose()


_PATTERN: dict[str, object] = {
    "time_sig": {"num": 4, "den": 4},
    "tempo_bpm": 120,
    "subdivision": "1/16",
    "bars": [],
}
_PARAMS: dict[str, object] = {
    "time_sig": {"num": 4, "den": 4},
    "num_bars": 1,
    "subdivision": "1/16",
    "tempo_bpm": 120,
    "voicing": "snare",
    "singles": True,
    "odd": False,
    "paradiddle": False,
}


def _rate_body(rating: int, **over: object) -> dict[str, object]:
    body: dict[str, object] = {
        "rating": rating,
        "tags": [],
        "note": None,
        "kind": "exercise",
        "pattern": _PATTERN,
        "params": _PARAMS,
        "seed": 7,
    }
    body.update(over)
    return body


async def test_rate_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/patterns2/rate", json=_rate_body(1))
    assert resp.status_code == 401


async def test_rate_upsert_then_change_then_remove(client: AsyncClient, outbox: Outbox) -> None:
    await _signed_in(client, outbox, "r1@example.com")

    up = await client.post("/patterns2/rate", json=_rate_body(-1, tags=["too_busy", "unmusical"]))
    assert up.status_code == 200
    assert up.json()["rating"] == -1
    assert set(up.json()["tags"]) == {"too_busy", "unmusical"}

    # Same content → upsert (no duplicate row), flip to like.
    up2 = await client.post("/patterns2/rate", json=_rate_body(1, tags=["groovy"]))
    assert up2.status_code == 200
    assert up2.json()["rating"] == 1
    assert up2.json()["id"] == up.json()["id"]  # same row

    # rating 0 removes it.
    rm = await client.post("/patterns2/rate", json=_rate_body(0))
    assert rm.status_code == 204


async def test_rate_rejects_unknown_tag(client: AsyncClient, outbox: Outbox) -> None:
    await _signed_in(client, outbox, "r2@example.com")
    resp = await client.post("/patterns2/rate", json=_rate_body(-1, tags=["nonsense"]))
    assert resp.status_code == 422


async def _make_admin(client: AsyncClient, email: str) -> None:
    # Flip is_admin directly in the test DB session used by the app.
    from sqlalchemy import update

    from drumgen.api import app
    from drumgen.db.engine import get_session
    from drumgen.db.models import User

    override = app.dependency_overrides[get_session]
    agen = override()
    session = await agen.__anext__()
    try:
        await session.execute(update(User).where(User.email == email).values(is_admin=True))
        await session.commit()
    finally:
        await agen.aclose()


async def test_admin_ratings_forbidden_for_plain_user(client: AsyncClient, outbox: Outbox) -> None:
    await _signed_in(client, outbox, "plain2@example.com")
    assert (await client.get("/admin/ratings")).status_code == 403


async def test_admin_ratings_list_summary_and_moderation(
    client: AsyncClient, outbox: Outbox
) -> None:
    await _signed_in(client, outbox, "boss@example.com")
    await _make_admin(client, "boss@example.com")

    # Seed two ratings (distinct content → distinct rows).
    await client.post("/patterns2/rate", json=_rate_body(1, tags=["groovy"]))
    other = {**_PATTERN, "tempo_bpm": 90}
    await client.post("/patterns2/rate", json=_rate_body(-1, tags=["too_busy"], pattern=other))

    page = await client.get("/admin/ratings")
    assert page.status_code == 200
    data = page.json()
    assert data["total"] == 2
    assert data["summary"]["likes"] == 1
    assert data["summary"]["dislikes"] == 1
    assert data["summary"]["top_dislike_tags"][0]["tag"] == "too_busy"
    assert data["items"][0]["rater_email"] == "boss@example.com"

    rid = data["items"][0]["id"]
    mod = await client.patch(f"/admin/ratings/{rid}", json={"moderated_out": True})
    assert mod.status_code == 200
    assert mod.json()["moderated_out"] is True

    # Default list excludes moderated rows; include_moderated shows them.
    assert (await client.get("/admin/ratings")).json()["total"] == 1
    assert (await client.get("/admin/ratings?include_moderated=true")).json()["total"] == 2
