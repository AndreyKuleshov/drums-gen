"""End-to-end auth flow tests against the ASGI app + test database."""

import urllib.parse

from httpx import AsyncClient

Outbox = list[dict[str, str]]


def token_in(box: Outbox, marker: str) -> str:
    """Pull the one-time token out of the link in the most recent matching email."""
    for message in reversed(box):
        for line in message["text"].splitlines():
            if marker in line and "token=" in line:
                query = urllib.parse.urlparse(line.strip()).query
                return urllib.parse.parse_qs(query)["token"][0]
    raise AssertionError(f"no {marker} link found in outbox")


_EMAIL = "drummer@example.com"
_PW = "sup3r-secret-pw"


async def _register(
    client: AsyncClient,
    outbox: Outbox,
    email: str = _EMAIL,
    password: str = _PW,
    name: str = "Drummer",
) -> str:
    resp = await client.post(
        "/auth/register",
        json={"email": email, "password": password, "display_name": name},
    )
    assert resp.status_code == 202
    return token_in(outbox, "/verify")


async def test_register_verify_login_me_logout(client: AsyncClient, outbox: Outbox) -> None:
    verify_token = await _register(client, outbox)

    # Verify activates the account and logs the user in (sets a session cookie).
    resp = await client.post("/auth/verify", json={"token": verify_token})
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == _EMAIL
    assert body["is_verified"] is True

    me = await client.get("/auth/me")
    assert me.status_code == 200
    assert me.json()["email"] == _EMAIL

    assert (await client.post("/auth/logout")).status_code == 204
    assert (await client.get("/auth/me")).status_code == 401


async def test_login_requires_verification(client: AsyncClient, outbox: Outbox) -> None:
    await _register(client, outbox)
    # Not verified yet → cannot log in.
    resp = await client.post("/auth/login", json={"email": _EMAIL, "password": _PW})
    assert resp.status_code == 403


async def test_login_after_verify(client: AsyncClient, outbox: Outbox) -> None:
    token = await _register(client, outbox)
    await client.post("/auth/verify", json={"token": token})
    await client.post("/auth/logout")

    good = await client.post("/auth/login", json={"email": _EMAIL, "password": _PW})
    assert good.status_code == 200
    assert (await client.get("/auth/me")).status_code == 200

    bad = await client.post("/auth/login", json={"email": _EMAIL, "password": "wrong-pass"})
    assert bad.status_code == 401


async def test_invalid_verify_token(client: AsyncClient) -> None:
    resp = await client.post("/auth/verify", json={"token": "not-a-real-token"})
    assert resp.status_code == 400


async def test_forgot_and_reset(client: AsyncClient, outbox: Outbox) -> None:
    token = await _register(client, outbox)
    await client.post("/auth/verify", json={"token": token})
    await client.post("/auth/logout")

    forgot = await client.post("/auth/forgot", json={"email": _EMAIL})
    assert forgot.status_code == 202
    reset_token = token_in(outbox, "/reset")

    new_pw = "brand-new-password"
    reset = await client.post("/auth/reset", json={"token": reset_token, "password": new_pw})
    assert reset.status_code == 200

    # Old password rejected, new one works.
    old = await client.post("/auth/login", json={"email": _EMAIL, "password": _PW})
    assert old.status_code == 401
    fresh = await client.post("/auth/login", json={"email": _EMAIL, "password": new_pw})
    assert fresh.status_code == 200


async def test_duplicate_register_does_not_leak(client: AsyncClient, outbox: Outbox) -> None:
    await _register(client, outbox)
    # Second registration with the same email returns the same 202 (no enumeration).
    resp = await client.post(
        "/auth/register",
        json={"email": _EMAIL, "password": "another-pass", "display_name": "Someone"},
    )
    assert resp.status_code == 202


async def test_forgot_unknown_email_is_quiet(client: AsyncClient, outbox: Outbox) -> None:
    resp = await client.post("/auth/forgot", json={"email": "nobody@example.com"})
    assert resp.status_code == 202
    assert outbox == []
