"""Symmetric encryption for third-party OAuth tokens stored at rest.

Discogs OAuth tokens grant access to a user's Discogs account, so they must not
sit in the database as plaintext. This module encrypts them with Fernet
(AES-128-CBC + HMAC) using a key derived from ``settings.token_encryption_key``.

The configured key can be any string: we derive a valid 32-byte urlsafe-base64
Fernet key from it via SHA-256, so operators don't have to produce a
Fernet-format value by hand (though a random one is still strongly recommended;
production startup rejects the known dev default).
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


def _fernet() -> Fernet:
    # Derive a deterministic 32-byte key from the configured secret. Using the
    # raw config value directly would require it to already be a valid Fernet
    # key; hashing lets any sufficiently-random string work.
    digest = hashlib.sha256(settings.token_encryption_key.encode()).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_token(plaintext: str | None) -> str | None:
    """Encrypt a token for storage. Returns None if given None."""
    if plaintext is None:
        return None
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_token(ciphertext: str | None) -> str | None:
    """Decrypt a stored token. Returns None if given None.

    Raises ValueError if the ciphertext can't be decrypted (wrong key or the
    value predates encryption), so callers can surface a "reconnect Discogs"
    message rather than silently using garbage.
    """
    if ciphertext is None:
        return None
    try:
        return _fernet().decrypt(ciphertext.encode()).decode()
    except (InvalidToken, ValueError) as exc:
        raise ValueError(
            "Stored token could not be decrypted. It may have been encrypted "
            "with a different TOKEN_ENCRYPTION_KEY, or stored before encryption "
            "was enabled. The account should be reconnected."
        ) from exc
