"""Account sharing management.

Endpoints for the owner (and admins) to manage who can access an account:

* invites   - create / list / revoke login-required invite links, and accept
              one (which creates a membership for the accepting user);
* members   - list, change role, remove;
* public    - the anonymous read-only link and its on/off privacy toggle.

All management endpoints operate on the account resolved by the account-context
dependency (default: the caller's own account; or a shared account via the
X-Account-Id header) and require admin-or-owner via require_account_write /
can_manage_sharing.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    AccountContext,
    get_current_user,
    require_account_read,
    require_account_write,
)
from app.core.config import settings
from app.db.deps import get_db
from app.models.core import (
    AccountInvite,
    AccountMembership,
    AccountPublicShare,
    ROLE_ADMIN,
    ROLE_VIEWER,
    User,
)
from app.schemas.sharing import (
    InviteCreate,
    InviteOut,
    MemberOut,
    MemberRoleUpdate,
    PublicShareOut,
    PublicShareUpdate,
)

router = APIRouter(prefix="/sharing", tags=["sharing"])


def _new_token() -> str:
    return secrets.token_urlsafe(32)


def _invite_url(token: str) -> str:
    return f"{settings.web_base_url.rstrip('/')}/invite/{token}"


def _public_url(token: str) -> str:
    return f"{settings.web_base_url.rstrip('/')}/shared/{token}"


def _require_manage(ctx: AccountContext) -> None:
    if not ctx.can_manage_sharing():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the account owner or an admin can manage sharing.",
        )


@router.get("/shared-with-me")
def shared_with_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List accounts other people have shared with the current user."""
    rows = db.execute(
        select(AccountMembership, User)
        .join(User, AccountMembership.owner_id == User.id)
        .where(AccountMembership.member_id == current_user.id)
        .order_by(AccountMembership.created_at.asc())
    ).all()
    return [
        {
            "owner_id": str(m.owner_id),
            "label": u.display_name or u.email,
            "role": m.role,
        }
        for m, u in rows
    ]


# ---- Invites ---------------------------------------------------------------

@router.post("/invites", response_model=InviteOut, status_code=status.HTTP_201_CREATED)
def create_invite(
    payload: InviteCreate,
    ctx: AccountContext = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    _require_manage(ctx)
    expires_at = None
    if payload.expires_in_hours is not None:
        expires_at = datetime.now(timezone.utc) + timedelta(hours=payload.expires_in_hours)
    invite = AccountInvite(
        owner_id=ctx.owner_id,
        created_by=ctx.user.id,
        role=payload.role,
        token=_new_token(),
        expires_at=expires_at,
        max_uses=payload.max_uses,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return _invite_out(invite)


@router.get("/invites", response_model=list[InviteOut])
def list_invites(
    ctx: AccountContext = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    _require_manage(ctx)
    rows = db.scalars(
        select(AccountInvite)
        .where(AccountInvite.owner_id == ctx.owner_id, AccountInvite.revoked == False)  # noqa: E712
        .order_by(AccountInvite.created_at.desc())
    ).all()
    return [_invite_out(i) for i in rows]


@router.delete("/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invite(
    invite_id: str,
    ctx: AccountContext = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    _require_manage(ctx)
    invite = db.scalar(
        select(AccountInvite).where(
            AccountInvite.id == invite_id, AccountInvite.owner_id == ctx.owner_id
        )
    )
    if invite is None:
        raise HTTPException(status_code=404, detail="Invite not found.")
    invite.revoked = True
    db.commit()
    return None


@router.post("/invites/{token}/accept", response_model=MemberOut)
def accept_invite(
    token: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Accept an invite (must be logged in). Creates or upgrades a membership."""
    invite = db.scalar(select(AccountInvite).where(AccountInvite.token == token))
    if invite is None or invite.revoked:
        raise HTTPException(status_code=404, detail="Invite is invalid or has been revoked.")
    if invite.expires_at is not None and invite.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Invite has expired.")
    if invite.max_uses is not None and invite.uses >= invite.max_uses:
        raise HTTPException(status_code=410, detail="Invite has reached its use limit.")
    if invite.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="You can't accept an invite to your own account.")

    membership = db.scalar(
        select(AccountMembership).where(
            AccountMembership.owner_id == invite.owner_id,
            AccountMembership.member_id == current_user.id,
        )
    )
    if membership is None:
        membership = AccountMembership(
            owner_id=invite.owner_id, member_id=current_user.id, role=invite.role
        )
        db.add(membership)
    else:
        # Upgrade role if the invite grants more (viewer -> admin), never downgrade.
        if invite.role == ROLE_ADMIN:
            membership.role = ROLE_ADMIN
    invite.uses += 1
    db.commit()
    db.refresh(membership)
    return MemberOut(
        member_id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
        role=membership.role,
    )


# ---- Members ---------------------------------------------------------------

@router.get("/members", response_model=list[MemberOut])
def list_members(
    ctx: AccountContext = Depends(require_account_read),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(AccountMembership, User)
        .join(User, AccountMembership.member_id == User.id)
        .where(AccountMembership.owner_id == ctx.owner_id)
        .order_by(AccountMembership.created_at.asc())
    ).all()
    return [
        MemberOut(
            member_id=str(m.member_id),
            email=u.email,
            display_name=u.display_name,
            role=m.role,
        )
        for m, u in rows
    ]


@router.patch("/members/{member_id}", response_model=MemberOut)
def update_member_role(
    member_id: str,
    payload: MemberRoleUpdate,
    ctx: AccountContext = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    _require_manage(ctx)
    membership = db.scalar(
        select(AccountMembership).where(
            AccountMembership.owner_id == ctx.owner_id,
            AccountMembership.member_id == member_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Member not found.")
    membership.role = payload.role
    db.commit()
    user = db.get(User, membership.member_id)
    return MemberOut(
        member_id=str(membership.member_id),
        email=user.email,
        display_name=user.display_name,
        role=membership.role,
    )


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    member_id: str,
    ctx: AccountContext = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    _require_manage(ctx)
    membership = db.scalar(
        select(AccountMembership).where(
            AccountMembership.owner_id == ctx.owner_id,
            AccountMembership.member_id == member_id,
        )
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Member not found.")
    db.delete(membership)
    db.commit()
    return None


# ---- Anonymous public read link -------------------------------------------

@router.get("/public", response_model=PublicShareOut)
def get_public_share(
    ctx: AccountContext = Depends(require_account_read),
    db: Session = Depends(get_db),
):
    share = db.scalar(select(AccountPublicShare).where(AccountPublicShare.owner_id == ctx.owner_id))
    if share is None:
        return PublicShareOut(enabled=False, token=None, public_url=None)
    return PublicShareOut(
        enabled=share.enabled,
        token=share.token,
        public_url=_public_url(share.token) if share.enabled else None,
    )


@router.put("/public", response_model=PublicShareOut)
def set_public_share(
    payload: PublicShareUpdate,
    ctx: AccountContext = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    """Turn the anonymous public read link on or off (the privacy toggle)."""
    _require_manage(ctx)
    share = db.scalar(select(AccountPublicShare).where(AccountPublicShare.owner_id == ctx.owner_id))
    if share is None:
        share = AccountPublicShare(owner_id=ctx.owner_id, token=_new_token(), enabled=payload.enabled)
        db.add(share)
    else:
        share.enabled = payload.enabled
    db.commit()
    db.refresh(share)
    return PublicShareOut(
        enabled=share.enabled,
        token=share.token,
        public_url=_public_url(share.token) if share.enabled else None,
    )


@router.post("/public/regenerate", response_model=PublicShareOut)
def regenerate_public_share(
    ctx: AccountContext = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    """Rotate the public link token, invalidating any previously shared link."""
    _require_manage(ctx)
    share = db.scalar(select(AccountPublicShare).where(AccountPublicShare.owner_id == ctx.owner_id))
    if share is None:
        share = AccountPublicShare(owner_id=ctx.owner_id, token=_new_token(), enabled=False)
        db.add(share)
    else:
        share.token = _new_token()
    db.commit()
    db.refresh(share)
    return PublicShareOut(
        enabled=share.enabled,
        token=share.token,
        public_url=_public_url(share.token) if share.enabled else None,
    )


def _invite_out(invite: AccountInvite) -> InviteOut:
    return InviteOut(
        id=str(invite.id),
        role=invite.role,
        token=invite.token,
        invite_url=_invite_url(invite.token),
        expires_at=invite.expires_at,
        max_uses=invite.max_uses,
        uses=invite.uses,
        revoked=invite.revoked,
    )
