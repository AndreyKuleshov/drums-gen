"""Avatar processing: validate an upload and re-encode to a square webp.

Re-encoding through Pillow strips EXIF/metadata and normalizes format, so we
never store an untrusted file verbatim. Files land on the media volume under
avatars/<uuid>.webp and are served back via the static /media mount.
"""

import contextlib
import uuid
from io import BytesIO
from pathlib import Path

from PIL import Image, UnidentifiedImageError

_SIZE = 256


class AvatarError(Exception):
    """The uploaded file is not a usable image."""


def process_avatar(raw: bytes, media_dir: str) -> str:
    """Write a normalized avatar and return its stored filename (e.g. `<uuid>.webp`)."""
    try:
        opened: Image.Image = Image.open(BytesIO(raw))
        opened.load()
    except (UnidentifiedImageError, OSError) as exc:
        raise AvatarError("Unsupported or corrupt image") from exc

    image: Image.Image = opened.convert("RGB")

    # Center-crop to a square, then downscale to the target size.
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    # Pillow's `resize` signature carries Unknown in its stubs; the call is sound.
    image = image.resize((_SIZE, _SIZE), Image.Resampling.LANCZOS)  # pyright: ignore[reportUnknownMemberType]

    name = f"{uuid.uuid4().hex}.webp"
    out_dir = Path(media_dir) / "avatars"
    out_dir.mkdir(parents=True, exist_ok=True)
    image.save(out_dir / name, format="WEBP", quality=88, method=6)
    return name


def remove_avatar(filename: str, media_dir: str) -> None:
    """Delete a previously stored avatar (best-effort)."""
    with contextlib.suppress(OSError):
        (Path(media_dir) / "avatars" / filename).unlink(missing_ok=True)
