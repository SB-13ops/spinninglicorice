"""Password hashing and JWT access-token helpers.

Kept deliberately small and dependency-light:

* passwords are hashed with bcrypt via ``pwdlib``;
* access tokens are signed JWTs (HS256) created and verified with ``pyjwt``.

All tuning knobs (secret, algorithm, expiry) live in ``app.core.config``.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from pwdlib.hashers.bcrypt import BcryptHasher

from app.core.config import settings

# A single bcrypt hasher instance. bcrypt is intentionally chosen over argon2
# to avoid a native build dependency in the container image; it is still a
# sound password hash. If you later add argon2 (pip install "pwdlib[argon2]"),
# add Argon2Hasher() first in this tuple so new hashes upgrade automatically.
_password_hash = PasswordHash((BcryptHasher(),))


def hash_password(plain_password: str) -> str:
    """Return a bcrypt hash for the given plaintext password."""
    return _password_hash.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plaintext password against a stored hash. Never raises."""
    try:
        return _password_hash.verify(plain_password, hashed_password)
    except Exception:
        return False


def create_access_token(
    subject: str | uuid.UUID,
    expires_minutes: int | None = None,
) -> str:
    """Create a signed JWT access token whose ``sub`` claim is the user id."""
    expire_minutes = (
        expires_minutes
        if expires_minutes is not None
        else settings.access_token_expire_minutes
    )
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Raises ``jwt.PyJWTError`` (or a subclass) if the token is invalid or
    expired; callers translate that into an HTTP 401.
    """
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )
