"""Tests for account profile editing and avatar upload."""

import io
import urllib.parse

from httpx import AsyncClient
from PIL import Image

Outbox = list[dict[str, str]]


def _token(box: Outbox, marker: str) -> str:
    for message in reversed(box):
        for line in message["text"].splitlines():
            if marker in line and "token=" in line:
                query = urllib.parse.urlparse(line.strip()).query
                return urllib.parse.parse_qs(query)["token"][0]
    raise AssertionError(f"no {marker} link found")


async def _signed_in(client: AsyncClient, outbox: Outbox) -> None:
    await client.post(
        "/auth/register",
        json={"email": "me@example.com", "password": "password123", "display_name": "Me"},
    )
    await client.post("/auth/verify", json={"token": _token(outbox, "/verify")})


def _png_bytes(size: tuple[int, int] = (400, 300)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, (200, 120, 40)).save(buf, format="PNG")
    return buf.getvalue()


async def test_update_profile(client: AsyncClient, outbox: Outbox) -> None:
    await _signed_in(client, outbox)
    resp = await client.patch("/account", json={"display_name": "New Name", "bio": "I drum."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["display_name"] == "New Name"
    assert body["bio"] == "I drum."

    # Persisted across requests.
    me = await client.get("/auth/me")
    assert me.json()["display_name"] == "New Name"


async def test_update_profile_requires_auth(client: AsyncClient) -> None:
    resp = await client.patch("/account", json={"display_name": "X", "bio": ""})
    assert resp.status_code == 401


async def test_avatar_upload(client: AsyncClient, outbox: Outbox) -> None:
    await _signed_in(client, outbox)
    resp = await client.post(
        "/account/avatar",
        files={"file": ("me.png", _png_bytes(), "image/png")},
    )
    assert resp.status_code == 200
    url = resp.json()["avatar_url"]
    assert url is not None
    assert url.startswith("/api/media/avatars/")
    assert url.endswith(".webp")


async def test_avatar_rejects_non_image(client: AsyncClient, outbox: Outbox) -> None:
    await _signed_in(client, outbox)
    resp = await client.post(
        "/account/avatar",
        files={"file": ("x.txt", b"not an image", "text/plain")},
    )
    assert resp.status_code == 400
