"""Request models for editing the account profile."""

from pydantic import BaseModel, Field, field_validator

_MAX_LINKS = 10
_MAX_LINK_LEN = 200


class ProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    bio: str = Field(default="", max_length=2000)
    social_links: list[str] = Field(default_factory=list, max_length=_MAX_LINKS)

    @field_validator("social_links")
    @classmethod
    def _clean_links(cls, links: list[str]) -> list[str]:
        """Trim, drop blanks, require http(s) URLs, cap the length. The platform
        each link maps to (its brand icon) is worked out on the client."""
        out: list[str] = []
        for raw in links:
            url = raw.strip()
            if not url:
                continue
            if not url.startswith(("http://", "https://")):
                url = f"https://{url}"
            if len(url) > _MAX_LINK_LEN:
                raise ValueError("link is too long")
            out.append(url)
        return out[:_MAX_LINKS]
