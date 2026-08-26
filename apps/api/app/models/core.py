import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text,
    UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(120))
    # Nullable: users created via a future OAuth-only flow may have no local
    # password. Password login requires this to be set.
    hashed_password: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    # Optional peer-payment handles for off-app swap/sale settlement. The app
    # never touches money; it just surfaces these so members can pay each other.
    venmo_handle: Mapped[str | None] = mapped_column(String(100))
    paypal_handle: Mapped[str | None] = mapped_column(String(150))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserPreference(Base):
    __tablename__ = "user_preferences"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    location_text: Mapped[str | None] = mapped_column(String(200))
    radius_miles: Mapped[int] = mapped_column(Integer, default=25)
    price_min: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    price_max: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict)


class ExternalAccount(Base):
    __tablename__ = "external_accounts"
    __table_args__ = (UniqueConstraint("user_id", "provider", name="uq_user_provider"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(40))
    external_user_id: Mapped[str | None] = mapped_column(String(200))
    username: Mapped[str | None] = mapped_column(String(200))
    access_token_encrypted: Mapped[str | None] = mapped_column(Text)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text)
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Artist(Base):
    __tablename__ = "artists"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(300), index=True)
    sort_name: Mapped[str | None] = mapped_column(String(300))


class Album(Base):
    __tablename__ = "albums"

    id: Mapped[uuid.UUID] = uuid_pk()
    title: Mapped[str] = mapped_column(String(500), index=True)
    release_year: Mapped[int | None] = mapped_column(Integer)
    album_type: Mapped[str | None] = mapped_column(String(50))


class Release(Base):
    __tablename__ = "releases"

    id: Mapped[uuid.UUID] = uuid_pk()
    album_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("albums.id"))
    title: Mapped[str] = mapped_column(String(500))
    country: Mapped[str | None] = mapped_column(String(80))
    release_year: Mapped[int | None] = mapped_column(Integer)
    catalog_number: Mapped[str | None] = mapped_column(String(120))
    label_name: Mapped[str | None] = mapped_column(String(250))
    pressing_text: Mapped[str | None] = mapped_column(String(300))
    barcode: Mapped[str | None] = mapped_column(String(100))
    runout_side_a: Mapped[str | None] = mapped_column(String(300))
    runout_side_b: Mapped[str | None] = mapped_column(String(300))
    image_url: Mapped[str | None] = mapped_column(Text)


class ReleaseArtist(Base):
    __tablename__ = "release_artists"
    # release_id + artist_id are a composite primary key below, which already
    # enforces uniqueness on the pair. A separate UniqueConstraint on the same
    # two columns would be redundant, so it is intentionally omitted.

    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("releases.id", ondelete="CASCADE"), primary_key=True
    )
    artist_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artists.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(50), default="primary")


class ExternalMapping(Base):
    __tablename__ = "external_mappings"
    __table_args__ = (UniqueConstraint("provider", "external_id", "entity_type", name="uq_external_mapping"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(String(40))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    external_id: Mapped[str] = mapped_column(String(200))


class CollectionItem(Base):
    __tablename__ = "collection_items"
    __table_args__ = (
        UniqueConstraint("user_id", "release_id", "copy_number", name="uq_collection_copy"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    release_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("releases.id"))
    copy_number: Mapped[int] = mapped_column(Integer, default=1)
    media_condition: Mapped[str | None] = mapped_column(String(20))
    sleeve_condition: Mapped[str | None] = mapped_column(String(20))
    purchase_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    purchase_date: Mapped[date | None] = mapped_column(Date)
    purchase_location: Mapped[str | None] = mapped_column(String(250))
    personal_notes: Mapped[str | None] = mapped_column(Text)
    personal_rating: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="collection")
    source: Mapped[str] = mapped_column(String(40), default="spinninglicorice")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WantlistItem(Base):
    __tablename__ = "wantlist_items"
    __table_args__ = (UniqueConstraint("user_id", "release_id", name="uq_user_want_release"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    release_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("releases.id"))
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    minimum_media_condition: Mapped[str | None] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(40), default="spinninglicorice")


class CollectorProfile(Base):
    __tablename__ = "collector_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    preferred_era_start: Mapped[int | None] = mapped_column(Integer)
    preferred_era_end: Mapped[int | None] = mapped_column(Integer)
    typical_price_low: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    typical_price_high: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    preferred_condition: Mapped[str | None] = mapped_column(String(20))
    pressing_preferences: Mapped[dict] = mapped_column(JSONB, default=dict)
    summary: Mapped[dict] = mapped_column(JSONB, default=dict)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CollectorAffinity(Base):
    __tablename__ = "collector_affinities"
    __table_args__ = (
        UniqueConstraint("user_id", "affinity_type", "affinity_key", name="uq_collector_affinity"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    affinity_type: Mapped[str] = mapped_column(String(40))
    affinity_key: Mapped[str] = mapped_column(String(300))
    score: Mapped[Decimal] = mapped_column(Numeric(6, 3))
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)


class Hunt(Base):
    __tablename__ = "hunts"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(200))
    natural_language_query: Mapped[str | None] = mapped_column(Text)
    is_auto: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HuntCriteria(Base):
    __tablename__ = "hunt_criteria"

    hunt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("hunts.id", ondelete="CASCADE"), primary_key=True
    )
    criteria: Mapped[dict] = mapped_column(JSONB, default=dict)


class MarketListing(Base):
    __tablename__ = "market_listings"
    __table_args__ = (UniqueConstraint("source", "external_listing_id", name="uq_market_listing"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    source: Mapped[str] = mapped_column(String(50))
    external_listing_id: Mapped[str] = mapped_column(String(200))
    release_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("releases.id"))
    title_raw: Mapped[str] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    shipping: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    media_condition: Mapped[str | None] = mapped_column(String(20))
    sleeve_condition: Mapped[str | None] = mapped_column(String(20))
    seller_name: Mapped[str | None] = mapped_column(String(250))
    listing_url: Mapped[str] = mapped_column(Text)
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HuntResult(Base):
    __tablename__ = "hunt_results"
    __table_args__ = (UniqueConstraint("hunt_id", "listing_id", name="uq_hunt_listing"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    hunt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("hunts.id"))
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("market_listings.id"))
    spinninglicorice_score: Mapped[int] = mapped_column(Integer)
    deal_label: Mapped[str] = mapped_column(String(30))
    score_breakdown: Mapped[dict] = mapped_column(JSONB, default=dict)
    explanation: Mapped[str | None] = mapped_column(Text)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    release_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("releases.id"))
    recommendation_type: Mapped[str] = mapped_column(String(40))
    match_score: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserFeedback(Base):
    __tablename__ = "user_feedback"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    target_type: Mapped[str] = mapped_column(String(40))
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    action: Mapped[str] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Event(Base):
    __tablename__ = "events"

    id: Mapped[uuid.UUID] = uuid_pk()
    provider: Mapped[str] = mapped_column(String(40))
    external_event_id: Mapped[str] = mapped_column(String(200))
    name: Mapped[str] = mapped_column(String(400))
    venue_name: Mapped[str | None] = mapped_column(String(300))
    city: Mapped[str | None] = mapped_column(String(150))
    region: Mapped[str | None] = mapped_column(String(100))
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ticket_url: Mapped[str | None] = mapped_column(Text)


class ScoutRecommendation(Base):
    __tablename__ = "scout_recommendations"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("events.id"))
    match_score: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSONB, default=dict)


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    notification_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(250))
    body: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict] = mapped_column(JSONB, default=dict)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String(40))
    job_type: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), default="queued")
    stats: Mapped[dict] = mapped_column(JSONB, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# ---------------------------------------------------------------------------
# Account sharing
#
# Every user "owns" their own account (their collection, hunts, DNA, etc.).
# Sharing lets an owner grant other people access to that account:
#
#   * AccountMembership  - a named person (member_id) has a role on an owner's
#                          account. role is "viewer" (read-only) or "admin"
#                          (read-write, may manage members/invites).
#   * AccountInvite      - a shareable, login-required invite link. Accepting it
#                          (while logged in) creates an AccountMembership.
#   * AccountPublicShare - an anonymous read-only link ("anyone with the link").
#                          `enabled` is the privacy on/off toggle. One row per
#                          account.
#
# The owner is NOT stored as a membership row; ownership is implicit and always
# outranks any membership.
# ---------------------------------------------------------------------------

ROLE_VIEWER = "viewer"
ROLE_ADMIN = "admin"
VALID_MEMBERSHIP_ROLES = (ROLE_VIEWER, ROLE_ADMIN)


class AccountMembership(Base):
    __tablename__ = "account_memberships"
    __table_args__ = (
        UniqueConstraint("owner_id", "member_id", name="uq_account_member"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20), default=ROLE_VIEWER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccountInvite(Base):
    __tablename__ = "account_invites"

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    role: Mapped[str] = mapped_column(String(20), default=ROLE_VIEWER)
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_uses: Mapped[int | None] = mapped_column(Integer)  # null = unlimited
    uses: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AccountPublicShare(Base):
    __tablename__ = "account_public_shares"

    id: Mapped[uuid.UUID] = uuid_pk()
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # The privacy toggle. When False, the anonymous link returns nothing.
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class OAuthIdentity(Base):
    """A social login linked to a SpinningLicorice user.

    A user may have several (e.g. Google + Facebook). (provider, subject) is
    unique — that pair is how a returning social login is matched to a user.
    """
    __tablename__ = "oauth_identities"
    __table_args__ = (
        UniqueConstraint("provider", "subject", name="uq_oauth_provider_subject"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(20))
    subject: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(320))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class HomeFeature(Base):
    """Per-account home-page personalization: a featured hero shown atop the
    home dashboard. One row per account (owner).

    feature_type is one of:
      * "album"  - a release from the collection; release_id set.
      * "artist" - an artist; artist_id set.
      * "custom" - a user-supplied image and/or text; custom_* set.
      * "default"- no personalization (the app's default hero).

    Fields not relevant to the chosen type are left null.
    """
    __tablename__ = "home_features"

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    feature_type: Mapped[str] = mapped_column(String(20), default="default", server_default="default")
    release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("releases.id", ondelete="SET NULL")
    )
    artist_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("artists.id", ondelete="SET NULL")
    )
    custom_image_url: Mapped[str | None] = mapped_column(Text)
    custom_title: Mapped[str | None] = mapped_column(String(200))
    custom_subtitle: Mapped[str | None] = mapped_column(String(300))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------------------
# Social layer: friend groups, message board, swap/sale listings
#
# Distinct from account sharing (which grants access to ONE owner's account).
# A friend group is a shared social space where each member keeps their own
# collection and they interact: talk (GroupMessage) and trade (GroupListing).
# ---------------------------------------------------------------------------

GROUP_ROLE_MEMBER = "member"
GROUP_ROLE_ADMIN = "admin"  # group creator/admin: can manage members & settings

LISTING_KIND_SWAP = "swap"
LISTING_KIND_SALE = "sale"
LISTING_STATUS_OPEN = "open"
LISTING_STATUS_CLOSED = "closed"


class FriendGroup(Base):
    __tablename__ = "friend_groups"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    # Optional link to an external Facebook group (Meta's API can't create or
    # post to groups, so we only store a link the members manage themselves).
    facebook_group_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GroupMembership(Base):
    __tablename__ = "group_memberships"
    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_member"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("friend_groups.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20), default=GROUP_ROLE_MEMBER)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GroupInvite(Base):
    __tablename__ = "group_invites"

    id: Mapped[uuid.UUID] = uuid_pk()
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("friend_groups.id", ondelete="CASCADE"), index=True
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_uses: Mapped[int | None] = mapped_column(Integer)
    uses: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    revoked: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class GroupMessage(Base):
    __tablename__ = "group_messages"

    id: Mapped[uuid.UUID] = uuid_pk()
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("friend_groups.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class GroupListing(Base):
    """A record a member offers to the group for swap or sale. Settlement is
    off-app via the seller's Venmo/PayPal handle; the app never holds money."""
    __tablename__ = "group_listings"

    id: Mapped[uuid.UUID] = uuid_pk()
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("friend_groups.id", ondelete="CASCADE"), index=True
    )
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Optional link to the seller's collection item / release for cover + title.
    release_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("releases.id", ondelete="SET NULL")
    )
    kind: Mapped[str] = mapped_column(String(10), default=LISTING_KIND_SWAP)  # swap | sale
    title: Mapped[str] = mapped_column(String(300))
    condition: Mapped[str | None] = mapped_column(String(60))
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))  # for sale
    currency: Mapped[str] = mapped_column(String(3), default="USD", server_default="USD")
    swap_wants: Mapped[str | None] = mapped_column(Text)  # what they'd swap for
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default=LISTING_STATUS_OPEN)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ListingInterest(Base):
    __tablename__ = "listing_interests"
    __table_args__ = (
        UniqueConstraint("listing_id", "user_id", name="uq_listing_interest"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    listing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("group_listings.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------------------------------------------------------------------------
# Collection value tracking
#
# ReleaseValuation caches "what is this release worth right now" (mid-point of
# Discogs price suggestions), so we don't re-fetch to value a collection.
# CollectionValueSnapshot records total worth at a point in time, with a
# per-holding breakdown so we can chart history and compute best/worst movers.
# ---------------------------------------------------------------------------

class ReleaseValuation(Base):
    __tablename__ = "release_valuations"

    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("releases.id", ondelete="CASCADE"), primary_key=True
    )
    estimated_value: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="USD", server_default="USD")
    source: Mapped[str] = mapped_column(String(40), default="discogs")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class CollectionValueSnapshot(Base):
    __tablename__ = "collection_value_snapshots"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    total_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    valued_count: Mapped[int] = mapped_column(Integer, default=0)  # items we had a value for
    # Per-holding breakdown at capture time: [{release_id, title, value}] — used
    # to compute best/worst movers by diffing against an earlier snapshot.
    holdings: Mapped[dict] = mapped_column(JSONB, default=dict)


# ---------------------------------------------------------------------------
# Public collector-to-collector board
#
# Distinct from the private FriendGroup listings (which stay scoped to a
# specific group): board posts are visible to every user of the app. A
# "trade" post references something the poster already owns (a
# CollectionItem); a "looking_for" post references something on their own
# wantlist (a WantlistItem) — so posting always starts from a record they've
# already tracked one way or the other, never a fresh freeform entry.
# ---------------------------------------------------------------------------

BOARD_POST_KIND_TRADE = "trade"
BOARD_POST_KIND_LOOKING_FOR = "looking_for"


class BoardPost(Base):
    __tablename__ = "board_posts"
    __table_args__ = (
        UniqueConstraint("user_id", "collection_item_id", name="uq_board_post_collection_item"),
        UniqueConstraint("user_id", "wantlist_item_id", name="uq_board_post_wantlist_item"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))  # "trade" | "looking_for"
    # Exactly one of these is set, matching `kind`.
    collection_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("collection_items.id", ondelete="CASCADE")
    )
    wantlist_item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("wantlist_items.id", ondelete="CASCADE")
    )
    release_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("releases.id", ondelete="CASCADE"), index=True
    )
    note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="open", server_default="open")  # open | closed
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )


class BoardPostComment(Base):
    __tablename__ = "board_post_comments"

    id: Mapped[uuid.UUID] = uuid_pk()
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("board_posts.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
