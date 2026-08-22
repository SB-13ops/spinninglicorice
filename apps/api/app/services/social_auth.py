"""Resolve a SpinningLicorice user from a social login profile."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.core import OAuthIdentity, User
from app.services.oauth_providers import SocialProfile


def find_or_create_user(db: Session, profile: SocialProfile) -> User:
    """Match a social profile to a user, creating/linking as needed.

    1. Known identity (provider+subject) -> that user.
    2. Else, if the email matches an existing user -> link this identity to them.
    3. Else -> create a new (passwordless) user and identity.
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

    if user is None:
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
