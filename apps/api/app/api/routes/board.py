from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import require_account_read, require_account_write
from app.db.deps import get_db
from app.services import board as board_service

router = APIRouter(prefix="/board", tags=["board"])


class TradePostCreate(BaseModel):
    collection_item_id: uuid.UUID
    note: str | None = Field(default=None, max_length=1000)


class LookingForPostCreate(BaseModel):
    wantlist_item_id: uuid.UUID
    note: str | None = Field(default=None, max_length=1000)


class CommentCreate(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


@router.get("")
def get_board(
    kind: str | None = Query(default=None, pattern="^(trade|looking_for)$"),
    limit: int = Query(default=30, ge=1, le=50),
    ctx=Depends(require_account_read),
    db: Session = Depends(get_db),
):
    """The public collector-to-collector board -- visible to every user,
    not scoped to any one account or friend group."""
    return {"posts": board_service.list_board_posts(db, ctx.owner_id, kind=kind, limit=limit)}


@router.get("/my-wantlist")
def get_my_wantlist_for_posting(
    ctx=Depends(require_account_read),
    db: Session = Depends(get_db),
):
    """Picker source for creating a 'looking for' post -- your own wantlist."""
    return {"items": board_service.list_my_wantlist(db, ctx.owner_id)}


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
    return {"id": str(post.id), "kind": post.kind, "status": post.status}


@router.delete("/{post_id}", status_code=204)
def delete_post(
    post_id: uuid.UUID,
    ctx=Depends(require_account_write),
    db: Session = Depends(get_db),
):
    if not board_service.remove_post(db, ctx.owner_id, post_id):
        raise HTTPException(status_code=404, detail="Posting not found.")
    return None


@router.get("/{post_id}/comments")
def get_comments(
    post_id: uuid.UUID,
    ctx=Depends(require_account_read),
    db: Session = Depends(get_db),
):
    return {"comments": board_service.list_comments(db, post_id)}


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
