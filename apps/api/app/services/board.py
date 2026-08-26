"""Public collector-to-collector board.

Distinct from the private FriendGroup listings, which stay scoped to a
specific group: board posts are visible to every user of the app. Posting
always starts from a record someone's already tracked one way or another --
a "trade" post references something in their own collection, a "looking_for"
post references something on their own wantlist -- rather than a freeform
entry, so the board can't be used to advertise something unrelated to actual
collecting activity.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import (
    Artist,
    BoardPost,
    BoardPostComment,
    CollectionItem,
    Release,
    ReleaseArtist,
    User,
    WantlistItem,
)

BOARD_POST_KIND_TRADE = "trade"
BOARD_POST_KIND_LOOKING_FOR = "looking_for"


def _release_artists(db: Session, release_id: uuid.UUID) -> list[str]:
    return list(
        db.scalars(
            select(Artist.name)
            .join(ReleaseArtist, ReleaseArtist.artist_id == Artist.id)
            .where(ReleaseArtist.release_id == release_id)
        ).all()
    )


def _poster_name(user: User | None) -> str:
    if user is None:
        return "A collector"
    return user.display_name or user.email.split("@")[0]


# ---- creating posts ---------------------------------------------------------

def create_trade_post(db: Session, user_id: uuid.UUID, collection_item_id: uuid.UUID, note: str | None) -> BoardPost:
    item = db.scalar(
        select(CollectionItem).where(CollectionItem.id == collection_item_id, CollectionItem.user_id == user_id)
    )
    if item is None:
        raise ValueError("That record isn't in your collection.")

    existing = db.scalar(
        select(BoardPost).where(BoardPost.user_id == user_id, BoardPost.collection_item_id == collection_item_id)
    )
    if existing is not None:
        if existing.status != "open":
            existing.status = "open"
            existing.note = note
            db.commit()
            db.refresh(existing)
        return existing

    post = BoardPost(
        user_id=user_id,
        kind=BOARD_POST_KIND_TRADE,
        collection_item_id=collection_item_id,
        release_id=item.release_id,
        note=note,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def create_looking_for_post(db: Session, user_id: uuid.UUID, wantlist_item_id: uuid.UUID, note: str | None) -> BoardPost:
    item = db.scalar(
        select(WantlistItem).where(WantlistItem.id == wantlist_item_id, WantlistItem.user_id == user_id)
    )
    if item is None:
        raise ValueError("That record isn't on your wantlist.")

    existing = db.scalar(
        select(BoardPost).where(BoardPost.user_id == user_id, BoardPost.wantlist_item_id == wantlist_item_id)
    )
    if existing is not None:
        if existing.status != "open":
            existing.status = "open"
            existing.note = note
            db.commit()
            db.refresh(existing)
        return existing

    post = BoardPost(
        user_id=user_id,
        kind=BOARD_POST_KIND_LOOKING_FOR,
        wantlist_item_id=wantlist_item_id,
        release_id=item.release_id,
        note=note,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def remove_post(db: Session, user_id: uuid.UUID, post_id: uuid.UUID) -> bool:
    post = db.scalar(select(BoardPost).where(BoardPost.id == post_id, BoardPost.user_id == user_id))
    if post is None:
        return False
    db.delete(post)
    db.commit()
    return True


# ---- reading the board -------------------------------------------------------

def _serialize_post(db: Session, post: BoardPost, viewer_id: uuid.UUID) -> dict:
    release = db.get(Release, post.release_id)
    poster = db.get(User, post.user_id)
    comment_count = db.scalar(
        select(BoardPostComment.id).where(BoardPostComment.post_id == post.id)
    )
    comment_count = len(
        db.scalars(select(BoardPostComment.id).where(BoardPostComment.post_id == post.id)).all()
    )

    condition = None
    max_price = None
    if post.kind == BOARD_POST_KIND_TRADE and post.collection_item_id:
        item = db.get(CollectionItem, post.collection_item_id)
        if item:
            condition = item.media_condition
    elif post.kind == BOARD_POST_KIND_LOOKING_FOR and post.wantlist_item_id:
        item = db.get(WantlistItem, post.wantlist_item_id)
        if item:
            condition = item.minimum_media_condition
            max_price = float(item.max_price) if item.max_price is not None else None

    return {
        "id": str(post.id),
        "kind": post.kind,
        "note": post.note,
        "status": post.status,
        "created_at": post.created_at.isoformat(),
        "release": {
            "id": str(release.id) if release else None,
            "title": release.title if release else "Unknown release",
            "artists": _release_artists(db, post.release_id) if release else [],
            "year": release.release_year if release else None,
            "image_url": release.image_url if release else None,
        },
        "poster": {
            "user_id": str(post.user_id),
            "display_name": _poster_name(poster),
        },
        "condition": condition,
        "max_price": max_price,
        "comment_count": comment_count,
        "is_own_post": post.user_id == viewer_id,
    }


def list_board_posts(
    db: Session,
    viewer_id: uuid.UUID,
    *,
    kind: str | None = None,
    limit: int = 30,
    before: datetime | None = None,
) -> list[dict]:
    stmt = select(BoardPost).where(BoardPost.status == "open")
    if kind:
        stmt = stmt.where(BoardPost.kind == kind)
    if before:
        stmt = stmt.where(BoardPost.created_at < before)
    stmt = stmt.order_by(BoardPost.created_at.desc()).limit(min(limit, 50))
    posts = db.scalars(stmt).all()
    return [_serialize_post(db, p, viewer_id) for p in posts]


# ---- comments ---------------------------------------------------------------

def add_comment(db: Session, user_id: uuid.UUID, post_id: uuid.UUID, message: str) -> dict:
    if not message.strip():
        raise ValueError("Comment can't be empty.")
    post = db.get(BoardPost, post_id)
    if post is None:
        raise ValueError("That posting no longer exists.")
    comment = BoardPostComment(post_id=post_id, user_id=user_id, message=message.strip())
    db.add(comment)
    db.commit()
    db.refresh(comment)
    author = db.get(User, user_id)
    return {
        "id": str(comment.id),
        "message": comment.message,
        "created_at": comment.created_at.isoformat(),
        "author": _poster_name(author),
        "user_id": str(user_id),
    }


def list_comments(db: Session, post_id: uuid.UUID) -> list[dict]:
    comments = db.scalars(
        select(BoardPostComment).where(BoardPostComment.post_id == post_id).order_by(BoardPostComment.created_at.asc())
    ).all()
    out = []
    for c in comments:
        author = db.get(User, c.user_id)
        out.append(
            {
                "id": str(c.id),
                "message": c.message,
                "created_at": c.created_at.isoformat(),
                "author": _poster_name(author),
                "user_id": str(c.user_id),
            }
        )
    return out


# ---- wantlist picker (for creating a "looking for" post) --------------------

def list_my_wantlist(db: Session, user_id: uuid.UUID) -> list[dict]:
    rows = db.execute(
        select(WantlistItem, Release)
        .join(Release, WantlistItem.release_id == Release.id)
        .where(WantlistItem.user_id == user_id)
        .order_by(Release.title)
    ).all()
    out = []
    for item, release in rows:
        out.append(
            {
                "wantlist_item_id": str(item.id),
                "release_id": str(release.id),
                "title": release.title,
                "artists": _release_artists(db, release.id),
                "year": release.release_year,
                "image_url": release.image_url,
                "max_price": float(item.max_price) if item.max_price is not None else None,
                "minimum_media_condition": item.minimum_media_condition,
            }
        )
    return out
