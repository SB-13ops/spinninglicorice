from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class InviteCreate(BaseModel):
    role: str = Field(default="viewer", pattern="^(viewer|admin)$")
    expires_in_hours: int | None = Field(default=168, ge=1, le=24 * 90)  # default 7 days
    max_uses: int | None = Field(default=None, ge=1, le=1000)


class InviteOut(BaseModel):
    id: str
    role: str
    token: str
    invite_url: str
    expires_at: datetime | None = None
    max_uses: int | None = None
    uses: int
    revoked: bool


class MemberOut(BaseModel):
    member_id: str
    email: str
    display_name: str | None = None
    role: str


class MemberRoleUpdate(BaseModel):
    role: str = Field(pattern="^(viewer|admin)$")


class PublicShareOut(BaseModel):
    enabled: bool
    token: str | None = None
    public_url: str | None = None


class PublicShareUpdate(BaseModel):
    enabled: bool
