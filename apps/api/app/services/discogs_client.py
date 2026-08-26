from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

import requests
from requests_oauthlib import OAuth1Session

from app.core.config import settings


REQUEST_TOKEN_URL = "https://api.discogs.com/oauth/request_token"
AUTHORIZE_URL = "https://www.discogs.com/oauth/authorize"
ACCESS_TOKEN_URL = "https://api.discogs.com/oauth/access_token"
API_BASE_URL = "https://api.discogs.com"


@dataclass
class DiscogsOAuthRequest:
    token: str
    token_secret: str
    authorization_url: str


@dataclass
class DiscogsAccessToken:
    token: str
    token_secret: str


class DiscogsClient:
    """Small Discogs API adapter.

    Discogs uses OAuth 1.0a for user-authorized operations. This adapter keeps
    provider-specific behavior out of the collection domain.
    """

    def __init__(
        self,
        *,
        access_token: str | None = None,
        access_token_secret: str | None = None,
    ):
        self.access_token = access_token
        self.access_token_secret = access_token_secret

    @staticmethod
    def _user_agent() -> str:
        # Discogs asks API clients to identify themselves.
        return "SpinningLicorice/0.1 +https://spinninglicorice.local"

    def begin_oauth(self) -> DiscogsOAuthRequest:
        oauth = OAuth1Session(
            settings.discogs_consumer_key,
            client_secret=settings.discogs_consumer_secret,
            callback_uri=settings.discogs_callback_url,
        )
        payload = oauth.fetch_request_token(REQUEST_TOKEN_URL)
        token = payload["oauth_token"]
        secret = payload["oauth_token_secret"]
        return DiscogsOAuthRequest(
            token=token,
            token_secret=secret,
            authorization_url=f"{AUTHORIZE_URL}?oauth_token={token}",
        )

    def finish_oauth(
        self,
        *,
        request_token: str,
        request_token_secret: str,
        verifier: str,
    ) -> DiscogsAccessToken:
        oauth = OAuth1Session(
            settings.discogs_consumer_key,
            client_secret=settings.discogs_consumer_secret,
            resource_owner_key=request_token,
            resource_owner_secret=request_token_secret,
            verifier=verifier,
        )
        payload = oauth.fetch_access_token(ACCESS_TOKEN_URL)
        return DiscogsAccessToken(
            token=payload["oauth_token"],
            token_secret=payload["oauth_token_secret"],
        )

    def _session(self) -> Any:
        # With per-user tokens: full OAuth 1.0a, needed for anything touching
        # a specific person's private data (their collection, wantlist,
        # profile edits).
        if self.access_token and self.access_token_secret:
            session = OAuth1Session(
                settings.discogs_consumer_key,
                client_secret=settings.discogs_consumer_secret,
                resource_owner_key=self.access_token,
                resource_owner_secret=self.access_token_secret,
            )
            session.headers.update({"User-Agent": self._user_agent()})
            return session
        # Without per-user tokens: Discogs' public, read-only endpoints
        # (searching the database, looking up a specific release) don't
        # actually require a connected user account — they just need the
        # app identified, via a plain key+secret pair rather than full OAuth.
        # This is what lets barcode scanning, cover search, and adding a
        # specific release work standalone, without asking someone to link
        # their personal Discogs account first.
        session = requests.Session()
        session.headers.update({"User-Agent": self._user_agent()})
        return session

    def _is_app_level(self) -> bool:
        return not (self.access_token and self.access_token_secret)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        # Discogs rate-limits authenticated calls (~60/min) and unauthenticated
        # calls more strictly (~25/min). On HTTP 429, honor the Retry-After
        # header and retry a few times with backoff so a Hunt refresh degrades
        # to "slower" rather than "failed".
        import time

        request_params = dict(params or {})
        if self._is_app_level():
            request_params["key"] = settings.discogs_consumer_key
            request_params["secret"] = settings.discogs_consumer_secret

        attempts = 0
        while True:
            response = self._session().get(
                f"{API_BASE_URL}{path}",
                params=request_params,
                timeout=30,
            )
            if response.status_code == 429 and attempts < 3:
                retry_after = response.headers.get("Retry-After")
                try:
                    delay = float(retry_after) if retry_after else 2.0 * (attempts + 1)
                except ValueError:
                    delay = 2.0 * (attempts + 1)
                time.sleep(min(delay, 10.0))
                attempts += 1
                continue
            response.raise_for_status()
            return response.json()


    def database_search(
        self,
        *,
        query: str | None = None,
        artist: str | None = None,
        release_title: str | None = None,
        year: int | None = None,
        country: str | None = None,
        barcode: str | None = None,
        per_page: int = 25,
        page: int = 1,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            "type": "release",
            "format": "Vinyl",
            "per_page": per_page,
            "page": page,
        }
        if query:
            params["q"] = query
        if artist:
            params["artist"] = artist
        if release_title:
            params["release_title"] = release_title
        if year:
            params["year"] = year
        if country:
            params["country"] = country
        if barcode:
            params["barcode"] = barcode
        return self._get("/database/search", params)

    def price_suggestions(self, release_id: int | str) -> dict[str, Any]:
        # Cache: price suggestions move slowly; a short TTL cuts repeated calls
        # across hunts without going stale enough to matter.
        from app.core.cache import cache_get_json, cache_set_json

        key = f"discogs:price:{release_id}"
        cached = cache_get_json(key)
        if cached is not None:
            return cached
        data = self._get(f"/marketplace/price_suggestions/{release_id}")
        cache_set_json(key, data, ttl=1800)  # 30 min
        return data

    def identity(self) -> dict[str, Any]:
        return self._get("/oauth/identity")

    def release(self, release_id: int | str) -> dict[str, Any]:
        # Cache: release metadata is effectively immutable, so cache it longer.
        from app.core.cache import cache_get_json, cache_set_json

        key = f"discogs:release:{release_id}"
        cached = cache_get_json(key)
        if cached is not None:
            return cached
        data = self._get(f"/releases/{release_id}")
        cache_set_json(key, data, ttl=86400)  # 24h
        return data

    def collection_page(
        self,
        *,
        username: str,
        page: int = 1,
        per_page: int = 100,
    ) -> dict[str, Any]:
        return self._get(
            f"/users/{username}/collection/folders/0/releases",
            {"page": page, "per_page": per_page},
        )

    def wantlist_page(
        self,
        *,
        username: str,
        page: int = 1,
        per_page: int = 100,
    ) -> dict[str, Any]:
        return self._get(
            f"/users/{username}/wants",
            {"page": page, "per_page": per_page},
        )

    def iter_collection(self, username: str) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            payload = self.collection_page(username=username, page=page)
            for item in payload.get("releases", []):
                yield item
            pagination = payload.get("pagination", {})
            if page >= int(pagination.get("pages", page)):
                break
            page += 1

    def iter_wantlist(self, username: str) -> Iterator[dict[str, Any]]:
        page = 1
        while True:
            payload = self.wantlist_page(username=username, page=page)
            for item in payload.get("wants", []):
                yield item
            pagination = payload.get("pagination", {})
            if page >= int(pagination.get("pages", page)):
                break
            page += 1


def client_for_account(account) -> "DiscogsClient":
    """Build a DiscogsClient from a stored ExternalAccount.

    This is the single place OAuth tokens are decrypted for use, so encryption
    at rest is transparent to callers. Raises RuntimeError if the account has no
    usable credentials (missing, or undecryptable — e.g. encrypted with an old
    key), which callers translate into a "reconnect Discogs" response.
    """
    from app.core.token_crypto import decrypt_token

    if not account or not account.access_token_encrypted or not account.refresh_token_encrypted:
        raise RuntimeError("Discogs OAuth credentials are incomplete.")
    try:
        access_token = decrypt_token(account.access_token_encrypted)
        access_token_secret = decrypt_token(account.refresh_token_encrypted)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc
    return DiscogsClient(
        access_token=access_token,
        access_token_secret=access_token_secret,
    )
