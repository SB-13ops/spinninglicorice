from __future__ import annotations

from pydantic import BaseModel, Field, HttpUrl


class HomeFeatureUpdate(BaseModel):
    feature_type: str = Field(pattern="^(album|artist|custom|default)$")
    release_id: str | None = None
    artist_id: str | None = None
    custom_image_url: str | None = None
    custom_title: str | None = Field(default=None, max_length=200)
    custom_subtitle: str | None = Field(default=None, max_length=300)


class HomeHero(BaseModel):
    type: str
    title: str
    subtitle: str | None = None
    image_url: str | None = None
    ref_id: str | None = None
