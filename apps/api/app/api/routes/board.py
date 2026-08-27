from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_account_read, require_account_write
from app.db.deps import get_db
from app.services import board as board_service

router = APIRouter(prefix="/board", tags=["board"])
logger = logging.getLogger(__name__)


class TradePostCreate(BaseModel):
    collection_item_id: uuid.UUID
    note: str | None = Field(default=None, max_length=1000)


class LookingForPostCreate(BaseModel):
    wantlist_item_id: uuid.UUID
    note: str | None = Field(default=None, max_length=1000)


class CommentCreate(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


def _log_and_fail(exc: Exception, action: str) -> HTTPException:
    # Without this, any unexpected backend error (a missing table because a
    # migration hasn't run, a bad query, anything) previously propagated as a
    # raw, unhandled crash. Browsers render that as an opaque network failure
    # ("Failed to fetch" in Chrome, "Load failed" in Safari) with no way to
    # tell what actually went wrong -- even though the real cause was known
    # right here. Logging it server-side means it's visible in Railway's
    # logs, and returning a clean HTTPException means the browser gets a
    # normal, readable error instead of a broken response.
    logger.exception("Board %s failed: %s", action, exc)
    return HTTPException(status_code=500, detail=f"Something went wrong {action}. Please try again.")


@router.get("")
def get_board(
    kind: str | None = Query(default=None, pattern="^(trade|looking_for)$"),
    limit: int = Query(default=30, ge=1, le=50),
    ctx=Depends(require_account_read),
    db: Session = Depends(get_db),
):
    """The public collector-to-collector board -- visible to every user,
    not scoped to any one account or friend group."""
    try:
        return {"posts": board_service.list_board_posts(db, ctx.owner_id, kind=kind, limit=limit)}
    except Exception as exc:
        raise _log_and_fail(exc, "loading the board")


@router.get("/my-wantlist")
def get_my_wantlist_for_posting(
    ctx=Depends(require_account_read),
    db: Session = Depends(get_db),
):
    """Picker source for creating a 'looking for' post -- your own wantlist."""
    try:
        return {"items": board_service.list_my_wantlist(db, ctx.owner_id)}
    except Exception as exc:
        raise _log_and_fail(exc, "loading your wantlist")


@router.post("/trade", status_code=201)
def post_trade(
    payload: TradePostCreate,
    ctx=Depends(require_account_write),
    db: Session = Depends(get_db),
):
    try:
        post = board_service.create_trade_post(db, ctx.owner_id, payload.collection_item_id, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise _log_and_fail(exc, "posting to the board")
    return {"id": str(post.id), "kind": post.kind, "status": post.status}


@router.post("/looking-for", status_code=201)
def post_looking_for(
    payload: LookingForPostCreate,
    ctx=Depends(require_account_write),
    db: Session = Depends(get_db),
):
    try:
        post = board_service.create_looking_for_post(db, ctx.owner_id, payload.wantlist_item_id, payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise _log_and_fail(exc, "posting to the board")
    return {"id": str(post.id), "kind": post.kind, "status": post.status}


@router.delete("/{post_id}", status_code=204)
def delete_post(
    post_id: uuid.UUID,
    ctx=Depends(require_account_write),
    db: Session = Depends(get_db),
):
    try:
        found = board_service.remove_post(db, ctx.owner_id, post_id)
    except Exception as exc:
        raise _log_and_fail(exc, "removing that posting")
    if not found:
        raise HTTPException(status_code=404, detail="Posting not found.")
    return None


@router.get("/{post_id}/comments")
def get_comments(
    post_id: uuid.UUID,
    ctx=Depends(require_account_read),
    db: Session = Depends(get_db),
):
    try:
        return {"comments": board_service.list_comments(db, post_id)}
    except Exception as exc:
        raise _log_and_fail(exc, "loading comments")


@router.post("/{post_id}/comments", status_code=201)
def post_comment(
    post_id: uuid.UUID,
    payload: CommentCreate,
    ctx=Depends(require_account_write),
    db: Session = Depends(get_db),
):
    try:
        return board_service.add_comment(db, ctx.owner_id, post_id, payload.message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise _log_and_fail(exc, "posting your comment")
