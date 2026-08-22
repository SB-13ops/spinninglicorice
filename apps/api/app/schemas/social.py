from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


# ---- Groups ----
class GroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    facebook_group_url: str | None = None


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    facebook_group_url: str | None = None


class GroupOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    facebook_group_url: str | None = None
    role: str
    member_count: int


class GroupInviteOut(BaseModel):
    id: str
    token: str
    invite_url: str
    expires_at: datetime | None = None
    max_uses: int | None = None
    uses: int


class GroupMemberOut(BaseModel):
    user_id: str
    display_name: str | None = None
    email: str
    role: str


# ---- Messages ----
class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class MessageOut(BaseModel):
    id: str
    user_id: str
    author: str
    body: str
    created_at: datetime


# ---- Listings ----
class ListingCreate(BaseModel):
    kind: str = Field(pattern="^(swap|sale)$")
    title: str = Field(min_length=1, max_length=300)
    release_id: str | None = None
    condition: str | None = Field(default=None, max_length=60)
    price: float | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", max_length=3)
    swap_wants: str | None = Field(default=None, max_length=2000)
    note: str | None = Field(default=None, max_length=2000)


class InterestOut(BaseModel):
    user_id: str
    display_name: str | None = None
    message: str | None = None
    venmo_handle: str | None = None
    paypal_handle: str | None = None


class ListingOut(BaseModel):
    id: str
    kind: str
    title: str
    image_url: str | None = None
    condition: str | None = None
    price: float | None = None
    currency: str
    swap_wants: str | None = None
    note: str | None = None
    status: str
    seller_id: str
    seller_name: str | None = None
    seller_venmo: str | None = None
    seller_paypal: str | None = None
    interest_count: int
    created_at: datetime


class InterestCreate(BaseModel):
    message: str | None = Field(default=None, max_length=1000)


class PaymentHandles(BaseModel):
    venmo_handle: str | None = Field(default=None, max_length=100)
    paypal_handle: str | None = Field(default=None, max_length=150)
