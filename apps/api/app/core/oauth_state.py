"""Transient storage for in-flight OAuth request tokens.

During a Discogs OAuth handshake we must remember, between the /connect call
and the /callback redirect, the request-token secret and which user started the
flow. The previous implementation kept this in a module-level dict, which:

* is lost whenever the process restarts (Railway restarts containers routinely,
  so a user mid-connect would hit "request token expired"); and
* does not work across multiple replicas (the callback may land on a different
  instance than /connect did).

This module provides a small store with two backends:

* ``RedisOAuthStateStore`` — used when ``REDIS_URL`` is configured. State is
  namespaced and expires automatically via Redis TTL. Survives restarts and is
  shared across replicas.
* ``InMemoryOAuthStateStore`` — a single-process fallback for local dev without
  Redis. Entries carry their own expiry timestamp.

``get_oauth_state_store()`` returns the right one based on settings.
"""
from __future__ import annotations

import json
import time
from typing import Optional, Tuple

from app.core.config import settings

# (request_token_secret, user_id)
StatePayload = Tuple[str, str]

_KEY_PREFIX = "oauth:discogs:"
_DEFAULT_TTL_SECONDS = 15 * 60  # OAuth handshakes are short-lived


class OAuthStateStore:
    """Interface for storing/retrieving pending OAuth state by request token."""

    def put(self, request_token: str, secret: str, user_id: str, ttl: int = _DEFAULT_TTL_SECONDS) -> None:
        raise NotImplementedError

    def pop(self, request_token: str) -> Optional[StatePayload]:
        """Retrieve and delete the state for a request token, or None."""
        raise NotImplementedError


class InMemoryOAuthStateStore(OAuthStateStore):
    def __init__(self) -> None:
        # request_token -> (secret, user_id, expires_at_epoch)
        self._data: dict[str, tuple[str, str, float]] = {}

    def _purge_expired(self) -> None:
        now = time.time()
        expired = [k for k, (_, _, exp) in self._data.items() if exp < now]
        for k in expired:
            self._data.pop(k, None)

    def put(self, request_token: str, secret: str, user_id: str, ttl: int = _DEFAULT_TTL_SECONDS) -> None:
        self._purge_expired()
        self._data[request_token] = (secret, user_id, time.time() + ttl)

    def pop(self, request_token: str) -> Optional[StatePayload]:
        self._purge_expired()
        entry = self._data.pop(request_token, None)
        if entry is None:
            return None
        secret, user_id, _ = entry
        return secret, user_id


class RedisOAuthStateStore(OAuthStateStore):
    def __init__(self, client) -> None:
        self._redis = client

    def put(self, request_token: str, secret: str, user_id: str, ttl: int = _DEFAULT_TTL_SECONDS) -> None:
        value = json.dumps({"secret": secret, "user_id": user_id})
        self._redis.set(_KEY_PREFIX + request_token, value, ex=ttl)

    def pop(self, request_token: str) -> Optional[StatePayload]:
        key = _KEY_PREFIX + request_token
        # Fetch then delete. GETDEL (Redis 6.2+) does this atomically; fall back
        # to get+delete if unavailable.
        try:
            raw = self._redis.getdel(key)
        except Exception:
            raw = self._redis.get(key)
            if raw is not None:
                self._redis.delete(key)
        if raw is None:
            return None
        if isinstance(raw, bytes):
            raw = raw.decode()
        data = json.loads(raw)
        return data["secret"], data["user_id"]


_store: Optional[OAuthStateStore] = None


def get_oauth_state_store() -> OAuthStateStore:
    """Return the process-wide OAuth state store, constructing it on first use."""
    global _store
    if _store is not None:
        return _store
    if settings.redis_url:
        import redis  # imported lazily so local dev without redis installed still runs

        client = redis.Redis.from_url(settings.redis_url)
        _store = RedisOAuthStateStore(client)
    else:
        _store = InMemoryOAuthStateStore()
    return _store


# --- Social-login CSRF state -------------------------------------------------
# The social login flow needs a short-lived CSRF `state` value round-tripped
# through the provider. We reuse the same store, namespaced separately. The
# stored value is the post-login redirect path within the web app.

_LOGIN_PREFIX = "oauth:login:"


class LoginStateStore:
    def __init__(self, backend: OAuthStateStore):
        self._b = backend

    def put(self, state: str, redirect_path: str, ttl: int = _DEFAULT_TTL_SECONDS) -> None:
        # Reuse the (secret, user_id) tuple slots to carry (redirect_path, "").
        self._b.put(_LOGIN_PREFIX + state, redirect_path, "", ttl=ttl)

    def pop(self, state: str) -> str | None:
        payload = self._b.pop(_LOGIN_PREFIX + state)
        if payload is None:
            return None
        redirect_path, _ = payload
        return redirect_path


def get_login_state_store() -> LoginStateStore:
    return LoginStateStore(get_oauth_state_store())
