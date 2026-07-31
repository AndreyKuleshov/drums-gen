"""Request models for editing the account profile."""

from pydantic import BaseModel, Field


class ProfileIn(BaseModel):
    display_name: str = Field(min_length=1, max_length=80)
    bio: str = Field(default="", max_length=2000)
