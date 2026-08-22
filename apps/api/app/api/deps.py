"""Authentication dependencies.

``get_current_user`` is the single entry point every protected route uses to
resolve the authenticated user from the request's ``Authorization: Bearer``
header. It replaces the old ``select(User).limit(1)`` "first user in the table"
pattern, which served one shared account to every visitor.
"""
from __future__ import annotations

import uuid

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.deps import get_db
from app.models.core import User

# tokenUrl is the login endpoint; it powers the "Authorize" button in the
# generated OpenAPI docs. It must match the mounted route path.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_CREDENTIALS_EXC = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """Resolve and return the authenticated, active user, or raise 401."""
    try:
        payload = decode_access_token(token)
        subject = payload.get("sub")
        if not subject:
            raise _CREDENTIALS_EXC
        user_id = uuid.UUID(str(subject))
    except (jwt.PyJWTError, ValueError):
        raise _CREDENTIALS_EXC

    user = db.get(User, user_id)
    if user is None:
        raise _CREDENTIALS_EXC
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


# ---------------------------------------------------------------------------
# Account context & sharing permissions
#
# A request operates on some account (a data owner). By default that's the
# caller's own account. To act on an account shared with them, the client sends
# the owner's id via the `X-Account-Id` header (or `account_id` query param).
#
# get_account_context resolves the caller's effective role on the target
# account:  "owner" > "admin" > "viewer".  require_account_read allows any of
# the three; require_account_write allows only owner/admin.
# ---------------------------------------------------------------------------
from dataclasses import dataclass  # noqa: E402
from typing import Optional  # noqa: E402

from fastapi import Header, Query  # noqa: E402

from app.models.core import (  # noqa: E402
    AccountMembership,
    ROLE_ADMIN,
    ROLE_VIEWER,
)

ROLE_OWNER = "owner"
# Rank for comparisons; higher = more privilege.
_ROLE_RANK = {ROLE_VIEWER: 1, ROLE_ADMIN: 2, ROLE_OWNER: 3}


@dataclass
class AccountContext:
    """Who is acting, on whose account, with what effective role."""
    user: User            # the authenticated caller
    owner_id: uuid.UUID   # the account being acted upon (scope queries by this)
    role: str             # "owner" | "admin" | "viewer"

    @property
    def is_owner(self) -> bool:
        return self.role == ROLE_OWNER

    def can_write(self) -> bool:
        return _ROLE_RANK[self.role] >= _ROLE_RANK[ROLE_ADMIN]

    def can_manage_sharing(self) -> bool:
        # Owner and admins may manage members/invites/public share.
        return _ROLE_RANK[self.role] >= _ROLE_RANK[ROLE_ADMIN]


def get_account_context(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    x_account_id: Optional[str] = Header(default=None, alias="X-Account-Id"),
    account_id: Optional[str] = Query(default=None),
) -> AccountContext:
    """Resolve the target account and the caller's role on it.

    No account specified -> the caller's own account (role owner).
    An account specified  -> must be the caller's own, or one they're a member
    of; otherwise 403.
    """
    raw = x_account_id or account_id
    if not raw:
        return AccountContext(user=current_user, owner_id=current_user.id, role=ROLE_OWNER)

    try:
        target_owner_id = uuid.UUID(str(raw))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid account id.")

    if target_owner_id == current_user.id:
        return AccountContext(user=current_user, owner_id=target_owner_id, role=ROLE_OWNER)

    membership = db.scalar(
        select(AccountMembership).where(
            AccountMembership.owner_id == target_owner_id,
            AccountMembership.member_id == current_user.id,
        )
    )
    if membership is None:
        # Don't reveal whether the account exists.
        raise HTTPException(status_code=403, detail="You don't have access to this account.")
    role = membership.role if membership.role in (ROLE_VIEWER, ROLE_ADMIN) else ROLE_VIEWER
    return AccountContext(user=current_user, owner_id=target_owner_id, role=role)


def require_account_read(
    ctx: AccountContext = Depends(get_account_context),
) -> AccountContext:
    """Any role (owner/admin/viewer) may read."""
    return ctx


def require_account_write(
    ctx: AccountContext = Depends(get_account_context),
) -> AccountContext:
    """Only owner/admin may write; viewers get 403."""
    if not ctx.can_write():
        raise HTTPException(
            status_code=403,
            detail="This account is shared with you as read-only.",
        )
    return ctx


# ---------------------------------------------------------------------------
# Friend-group membership guards
# ---------------------------------------------------------------------------
from app.models.core import (  # noqa: E402
    FriendGroup,
    GroupMembership,
    GROUP_ROLE_ADMIN,
)


@dataclass
class GroupContext:
    user: User
    group: FriendGroup
    role: str  # "member" | "admin"

    @property
    def is_group_admin(self) -> bool:
        return self.role == GROUP_ROLE_ADMIN


def require_group_member(
    group_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> GroupContext:
    """Resolve group membership for the current user, or 403/404."""
    try:
        gid = uuid.UUID(group_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid group id.")
    group = db.get(FriendGroup, gid)
    if group is None:
        raise HTTPException(status_code=404, detail="Group not found.")
    membership = db.scalar(
        select(GroupMembership).where(
            GroupMembership.group_id == gid,
            GroupMembership.user_id == current_user.id,
        )
    )
    if membership is None:
        # Don't distinguish "not a member" from "no such group" for privacy.
        raise HTTPException(status_code=403, detail="You're not a member of this group.")
    return GroupContext(user=current_user, group=group, role=membership.role)


def require_group_admin(
    ctx: GroupContext = Depends(require_group_member),
) -> GroupContext:
    if not ctx.is_group_admin:
        raise HTTPException(status_code=403, detail="Only a group admin can do that.")
    return ctx
