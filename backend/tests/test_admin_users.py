"""Tests for admin user management (list + grant/revoke admin)."""

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


async def _signed_in(client: AsyncClient, outbox: Outbox, email: str) -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "display_name": email.split("@")[0]},
    )
    me = await client.post("/auth/verify", json={"token": _token(outbox, "/verify")})
    return me.json()["id"]


async def _login(client: AsyncClient, email: str) -> None:
    resp = await client.post("/auth/login", json={"email": email, "password": "password123"})
    assert resp.status_code == 200


async def _make_admin(email: str) -> None:
    from sqlalchemy import update

    from drumgen.api import app
    from drumgen.db.engine import get_session
    from drumgen.db.models import User

    agen = app.dependency_overrides[get_session]()
    session = await agen.__anext__()
    try:
        await session.execute(update(User).where(User.email == email).values(is_admin=True))
        await session.commit()
    finally:
        await agen.aclose()


async def test_admin_users_forbidden_for_plain_user(client: AsyncClient, outbox: Outbox) -> None:
    await _signed_in(client, outbox, "plain@example.com")
    assert (await client.get("/admin/users")).status_code == 403


async def test_admin_lists_and_grants(client: AsyncClient, outbox: Outbox) -> None:
    await _signed_in(client, outbox, "boss@example.com")
    await client.post("/auth/logout")
    other_id = await _signed_in(client, outbox, "member@example.com")
    await client.post("/auth/logout")

    await _login(client, "boss@example.com")
    await _make_admin("boss@example.com")

    listing = await client.get("/admin/users")
    assert listing.status_code == 200
    emails = {row["email"] for row in listing.json()}
    assert {"boss@example.com", "member@example.com"} <= emails

    granted = await client.patch(f"/admin/users/{other_id}", json={"is_admin": True})
    assert granted.status_code == 200
    assert granted.json()["is_admin"] is True


async def test_admin_cannot_revoke_own_admin(client: AsyncClient, outbox: Outbox) -> None:
    own_id = await _signed_in(client, outbox, "self@example.com")
    await _make_admin("self@example.com")
    resp = await client.patch(f"/admin/users/{own_id}", json={"is_admin": False})
    assert resp.status_code == 400


async def test_patch_unknown_user_404(client: AsyncClient, outbox: Outbox) -> None:
    await _signed_in(client, outbox, "boss2@example.com")
    await _make_admin("boss2@example.com")
    missing = "00000000-0000-0000-0000-000000000000"
    resp = await client.patch(f"/admin/users/{missing}", json={"is_admin": True})
    assert resp.status_code == 404
