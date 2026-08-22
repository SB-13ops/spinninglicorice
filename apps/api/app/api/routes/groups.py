"""Friend groups — the container for the social layer.

A group is a shared space where members each keep their own collection and
interact (messages, swap/sale listings). Group admins (the creator, plus anyone
promoted) can manage members, invites, and settings.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    GroupContext,
    get_current_user,
    require_group_admin,
    require_group_member,
)
from app.core.config import settings
from app.db.deps import get_db
from app.models.core import (
    FriendGroup,
    GroupInvite,
    GroupMembership,
    GROUP_ROLE_ADMIN,
    GROUP_ROLE_MEMBER,
    User,
)
from app.schemas.social import (
    GroupCreate,
    GroupInviteOut,
    GroupMemberOut,
    GroupOut,
    GroupUpdate,
)

router = APIRouter(prefix="/groups", tags=["groups"])


def _group_invite_url(token: str) -> str:
    return f"{settings.web_base_url.rstrip('/')}/groups/join/{token}"


def _member_count(db: Session, group_id) -> int:
    return db.scalar(
        select(func.count()).select_from(GroupMembership).where(GroupMembership.group_id == group_id)
    ) or 0


@router.post("", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
def create_group(
    payload: GroupCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    group = FriendGroup(
        name=payload.name,
        description=payload.description,
        facebook_group_url=payload.facebook_group_url,
        created_by=current_user.id,
    )
    db.add(group)
    db.flush()
    # Creator is the first admin member.
    db.add(GroupMembership(group_id=group.id, user_id=current_user.id, role=GROUP_ROLE_ADMIN))
    db.commit()
    db.refresh(group)
    return GroupOut(
        id=str(group.id),
        name=group.name,
        description=group.description,
        facebook_group_url=group.facebook_group_url,
        role=GROUP_ROLE_ADMIN,
        member_count=1,
    )


@router.get("", response_model=list[GroupOut])
def list_my_groups(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(FriendGroup, GroupMembership.role)
        .join(GroupMembership, GroupMembership.group_id == FriendGroup.id)
        .where(GroupMembership.user_id == current_user.id)
        .order_by(FriendGroup.created_at.desc())
    ).all()
    return [
        GroupOut(
            id=str(g.id),
            name=g.name,
            description=g.description,
            facebook_group_url=g.facebook_group_url,
            role=role,
            member_count=_member_count(db, g.id),
        )
        for g, role in rows
    ]


@router.get("/{group_id}", response_model=GroupOut)
def get_group(ctx: GroupContext = Depends(require_group_member), db: Session = Depends(get_db)):
    g = ctx.group
    return GroupOut(
        id=str(g.id),
        name=g.name,
        description=g.description,
        facebook_group_url=g.facebook_group_url,
        role=ctx.role,
        member_count=_member_count(db, g.id),
    )


@router.patch("/{group_id}", response_model=GroupOut)
def update_group(
    payload: GroupUpdate,
    ctx: GroupContext = Depends(require_group_admin),
    db: Session = Depends(get_db),
):
    g = ctx.group
    if payload.name is not None:
        g.name = payload.name
    if payload.description is not None:
        g.description = payload.description
    if payload.facebook_group_url is not None:
        g.facebook_group_url = payload.facebook_group_url
    db.commit()
    db.refresh(g)
    return GroupOut(
        id=str(g.id),
        name=g.name,
        description=g.description,
        facebook_group_url=g.facebook_group_url,
        role=ctx.role,
        member_count=_member_count(db, g.id),
    )


# ---- Invites ----

@router.post("/{group_id}/invites", response_model=GroupInviteOut, status_code=201)
def create_group_invite(
    ctx: GroupContext = Depends(require_group_admin),
    db: Session = Depends(get_db),
    expires_in_hours: int = 168,
    max_uses: int | None = None,
):
    invite = GroupInvite(
        group_id=ctx.group.id,
        created_by=ctx.user.id,
        token=secrets.token_urlsafe(32),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=expires_in_hours),
        max_uses=max_uses,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return GroupInviteOut(
        id=str(invite.id),
        token=invite.token,
        invite_url=_group_invite_url(invite.token),
        expires_at=invite.expires_at,
        max_uses=invite.max_uses,
        uses=invite.uses,
    )


@router.post("/join/{token}", response_model=GroupOut)
def join_group(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    invite = db.scalar(select(GroupInvite).where(GroupInvite.token == token))
    if invite is None or invite.revoked:
        raise HTTPException(status_code=404, detail="Invite is invalid or has been revoked.")
    if invite.expires_at is not None and invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invite has expired.")
    if invite.max_uses is not None and invite.uses >= invite.max_uses:
        raise HTTPException(status_code=410, detail="Invite has reached its use limit.")

    existing = db.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == invite.group_id,
            GroupMembership.user_id == current_user.id,
        )
    )
    if existing is None:
        db.add(
            GroupMembership(
                group_id=invite.group_id, user_id=current_user.id, role=GROUP_ROLE_MEMBER
            )
        )
        invite.uses += 1
        db.commit()

    group = db.get(FriendGroup, invite.group_id)
    return GroupOut(
        id=str(group.id),
        name=group.name,
        description=group.description,
        facebook_group_url=group.facebook_group_url,
        role=GROUP_ROLE_MEMBER if existing is None else existing.role,
        member_count=_member_count(db, group.id),
    )


# ---- Members ----

@router.get("/{group_id}/members", response_model=list[GroupMemberOut])
def list_group_members(
    ctx: GroupContext = Depends(require_group_member),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(GroupMembership, User)
        .join(User, GroupMembership.user_id == User.id)
        .where(GroupMembership.group_id == ctx.group.id)
        .order_by(GroupMembership.created_at.asc())
    ).all()
    return [
        GroupMemberOut(
            user_id=str(m.user_id),
            display_name=u.display_name,
            email=u.email,
            role=m.role,
        )
        for m, u in rows
    ]


@router.delete("/{group_id}/members/{user_id}", status_code=204)
def remove_member(
    user_id: str,
    ctx: GroupContext = Depends(require_group_admin),
    db: Session = Depends(get_db),
):
    if str(ctx.user.id) == user_id:
        raise HTTPException(status_code=400, detail="Use 'leave' to remove yourself.")
    membership = db.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == ctx.group.id,
            GroupMembership.user_id == user_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Member not found.")
    db.delete(membership)
    db.commit()
    return None


@router.post("/{group_id}/leave", status_code=204)
def leave_group(
    ctx: GroupContext = Depends(require_group_member),
    db: Session = Depends(get_db),
):
    membership = db.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == ctx.group.id,
            GroupMembership.user_id == ctx.user.id,
        )
    )
    # If the last admin leaves, promote the earliest remaining member so the
    # group isn't left adminless.
    if ctx.is_group_admin:
        other_admins = db.scalar(
            select(func.count()).select_from(GroupMembership).where(
                GroupMembership.group_id == ctx.group.id,
                GroupMembership.role == GROUP_ROLE_ADMIN,
                GroupMembership.user_id != ctx.user.id,
            )
        ) or 0
        if other_admins == 0:
            next_member = db.scalar(
                select(GroupMembership)
                .where(
                    GroupMembership.group_id == ctx.group.id,
                    GroupMembership.user_id != ctx.user.id,
                )
                .order_by(GroupMembership.created_at.asc())
                .limit(1)
            )
            if next_member is not None:
                next_member.role = GROUP_ROLE_ADMIN
    db.delete(membership)
    db.commit()
    return None
