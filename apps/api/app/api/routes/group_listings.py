"""Group swap/sale listings.

A member lists a record (optionally from their collection) for swap or sale.
Other members express interest. Settlement is OFF-APP: when there's mutual
interest, the seller's Venmo/PayPal handle is surfaced so members can pay each
other directly. The app never holds funds.
"""
from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import GroupContext, get_current_user, require_group_member
from app.db.deps import get_db
from app.models.core import (
    GroupListing,
    ListingInterest,
    LISTING_KIND_SALE,
    LISTING_STATUS_CLOSED,
    LISTING_STATUS_OPEN,
    Release,
    User,
)
from app.schemas.social import (
    InterestCreate,
    InterestOut,
    ListingCreate,
    ListingOut,
    PaymentHandles,
)

router = APIRouter(prefix="/groups/{group_id}/listings", tags=["group-listings"])


def _listing_out(db: Session, listing: GroupListing, seller: User) -> ListingOut:
    image_url = None
    if listing.release_id:
        image_url = db.scalar(select(Release.image_url).where(Release.id == listing.release_id))
    interest_count = db.scalar(
        select(func.count()).select_from(ListingInterest).where(
            ListingInterest.listing_id == listing.id
        )
    ) or 0
    return ListingOut(
        id=str(listing.id),
        kind=listing.kind,
        title=listing.title,
        image_url=image_url,
        condition=listing.condition,
        price=float(listing.price) if listing.price is not None else None,
        currency=listing.currency,
        swap_wants=listing.swap_wants,
        note=listing.note,
        status=listing.status,
        seller_id=str(listing.seller_id),
        seller_name=seller.display_name or seller.email,
        # Payment handles are surfaced so buyers can settle off-app.
        seller_venmo=seller.venmo_handle,
        seller_paypal=seller.paypal_handle,
        interest_count=interest_count,
        created_at=listing.created_at,
    )


@router.get("", response_model=list[ListingOut])
def list_listings(
    ctx: GroupContext = Depends(require_group_member),
    db: Session = Depends(get_db),
    include_closed: bool = False,
):
    stmt = (
        select(GroupListing, User)
        .join(User, GroupListing.seller_id == User.id)
        .where(GroupListing.group_id == ctx.group.id)
    )
    if not include_closed:
        stmt = stmt.where(GroupListing.status == LISTING_STATUS_OPEN)
    rows = db.execute(stmt.order_by(GroupListing.created_at.desc())).all()
    return [_listing_out(db, listing, seller) for listing, seller in rows]


@router.post("", response_model=ListingOut, status_code=201)
def create_listing(
    payload: ListingCreate,
    ctx: GroupContext = Depends(require_group_member),
    db: Session = Depends(get_db),
):
    if payload.kind == LISTING_KIND_SALE and payload.price is None:
        raise HTTPException(status_code=400, detail="A sale listing needs a price.")
    release_uuid = None
    if payload.release_id:
        try:
            release_uuid = uuid.UUID(payload.release_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid release_id.")

    listing = GroupListing(
        group_id=ctx.group.id,
        seller_id=ctx.user.id,
        release_id=release_uuid,
        kind=payload.kind,
        title=payload.title,
        condition=payload.condition,
        price=Decimal(str(payload.price)) if payload.price is not None else None,
        currency=payload.currency,
        swap_wants=payload.swap_wants,
        note=payload.note,
        status=LISTING_STATUS_OPEN,
    )
    db.add(listing)
    db.commit()
    db.refresh(listing)
    return _listing_out(db, listing, ctx.user)


@router.post("/{listing_id}/interest", response_model=ListingOut)
def express_interest(
    listing_id: str,
    payload: InterestCreate,
    ctx: GroupContext = Depends(require_group_member),
    db: Session = Depends(get_db),
):
    listing = _get_group_listing(db, ctx, listing_id)
    if listing.seller_id == ctx.user.id:
        raise HTTPException(status_code=400, detail="You can't express interest in your own listing.")
    if listing.status != LISTING_STATUS_OPEN:
        raise HTTPException(status_code=409, detail="This listing is closed.")

    existing = db.scalar(
        select(ListingInterest).where(
            ListingInterest.listing_id == listing.id,
            ListingInterest.user_id == ctx.user.id,
        )
    )
    if existing is None:
        db.add(
            ListingInterest(
                listing_id=listing.id, user_id=ctx.user.id, message=payload.message
            )
        )
        db.commit()
    seller = db.get(User, listing.seller_id)
    return _listing_out(db, listing, seller)


@router.get("/{listing_id}/interest", response_model=list[InterestOut])
def list_interest(
    listing_id: str,
    ctx: GroupContext = Depends(require_group_member),
    db: Session = Depends(get_db),
):
    """Interested members. Only the seller sees the full list (with contact
    handles); others just see their own interest to avoid leaking who's buying."""
    listing = _get_group_listing(db, ctx, listing_id)
    stmt = (
        select(ListingInterest, User)
        .join(User, ListingInterest.user_id == User.id)
        .where(ListingInterest.listing_id == listing.id)
    )
    if listing.seller_id != ctx.user.id:
        stmt = stmt.where(ListingInterest.user_id == ctx.user.id)
    rows = db.execute(stmt.order_by(ListingInterest.created_at.asc())).all()
    return [
        InterestOut(
            user_id=str(i.user_id),
            display_name=u.display_name,
            message=i.message,
            # Interested buyer's handles are shown to the seller for settlement.
            venmo_handle=u.venmo_handle,
            paypal_handle=u.paypal_handle,
        )
        for i, u in rows
    ]


@router.post("/{listing_id}/close", response_model=ListingOut)
def close_listing(
    listing_id: str,
    ctx: GroupContext = Depends(require_group_member),
    db: Session = Depends(get_db),
):
    listing = _get_group_listing(db, ctx, listing_id)
    if listing.seller_id != ctx.user.id and not ctx.is_group_admin:
        raise HTTPException(status_code=403, detail="Only the seller or a group admin can close this.")
    listing.status = LISTING_STATUS_CLOSED
    db.commit()
    seller = db.get(User, listing.seller_id)
    return _listing_out(db, listing, seller)


def _get_group_listing(db: Session, ctx: GroupContext, listing_id: str) -> GroupListing:
    try:
        lid = uuid.UUID(listing_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid listing id.")
    listing = db.get(GroupListing, lid)
    if listing is None or listing.group_id != ctx.group.id:
        raise HTTPException(status_code=404, detail="Listing not found.")
    return listing
