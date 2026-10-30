"""Resolve a SpinningLicorice user from a social login profile."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import OAuthIdentity, User
from app.services.oauth_providers import SocialProfile


class EmailInUseError(Exception):
    """An unverified social email matches an existing account."""


def find_or_create_user(db: Session, profile: SocialProfile) -> User:
    """Match a social profile to a user, creating/linking as needed.

    1. Known identity (provider+subject) -> that user.
    2. Else, if the provider-verified email matches an existing user -> link
       this identity to them.
    3. Else -> create a new (passwordless) user and identity.

    Raises EmailInUseError if an unverified email collides with an existing
    account, since linking on an unverified email would hand that account to
    whoever controls the social profile.
    """
    identity = db.scalar(
        select(OAuthIdentity).where(
            OAuthIdentity.provider == profile.provider,
            OAuthIdentity.subject == profile.subject,
        )
    )
    if identity is not None:
        return db.get(User, identity.user_id)

    user = None
    if profile.email:
        user = db.scalar(select(User).where(User.email == profile.email.lower().strip()))

    if user is not None:
        if not profile.email_verified:
            raise EmailInUseError(profile.email)
        # Password registration doesn't verify email ownership, so an existing
        # password may have been set by someone squatting on this address
        # before its real owner arrived. The provider just proved ownership,
        # so drop the unverified password rather than leave it as a backdoor.
        user.hashed_password = None
    else:
        user = User(
            email=(profile.email or f"{profile.provider}_{profile.subject}@users.noreply.spinninglicorice").lower().strip(),
            display_name=profile.name,
            hashed_password=None,  # social-only account
            is_active=True,
        )
        db.add(user)
        db.flush()  # assign user.id

    db.add(
        OAuthIdentity(
            user_id=user.id,
            provider=profile.provider,
            subject=profile.subject,
            email=profile.email,
        )
    )
    db.commit()
    db.refresh(user)
    return user
