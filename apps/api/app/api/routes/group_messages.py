"""Group message board.

Post + fetch-recent, with a `since` cursor so the web app can poll for new
messages efficiently. Deliberately simple (no WebSockets) but shaped so a
real-time transport can be layered on later without changing the data model:
the message store and the read API stay the same; only delivery changes.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import GroupContext, require_group_member
from app.db.deps import get_db
from app.models.core import GroupMessage, User
from app.schemas.social import MessageCreate, MessageOut

router = APIRouter(prefix="/groups/{group_id}/messages", tags=["group-messages"])


@router.get("", response_model=list[MessageOut])
def list_messages(
    ctx: GroupContext = Depends(require_group_member),
    db: Session = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    since: datetime | None = Query(default=None, description="Return messages after this timestamp"),
):
    stmt = select(GroupMessage, User).join(User, GroupMessage.user_id == User.id).where(
        GroupMessage.group_id == ctx.group.id
    )
    if since is not None:
        stmt = stmt.where(GroupMessage.created_at > since)
        stmt = stmt.order_by(GroupMessage.created_at.asc()).limit(limit)
        rows = db.execute(stmt).all()
    else:
        # Newest first, capped, then returned oldest->newest for display.
        stmt = stmt.order_by(GroupMessage.created_at.desc()).limit(limit)
        rows = list(reversed(db.execute(stmt).all()))
    return [
        MessageOut(
            id=str(msg.id),
            user_id=str(msg.user_id),
            author=u.display_name or u.email,
            body=msg.body,
            created_at=msg.created_at,
        )
        for msg, u in rows
    ]


@router.post("", response_model=MessageOut, status_code=201)
def post_message(
    payload: MessageCreate,
    ctx: GroupContext = Depends(require_group_member),
    db: Session = Depends(get_db),
):
    msg = GroupMessage(group_id=ctx.group.id, user_id=ctx.user.id, body=payload.body)
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return MessageOut(
        id=str(msg.id),
        user_id=str(msg.user_id),
        author=ctx.user.display_name or ctx.user.email,
        body=msg.body,
        created_at=msg.created_at,
    )
