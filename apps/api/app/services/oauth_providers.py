"""Social login providers (Google, Facebook).

Implements the OAuth 2.0 authorization-code flow at the HTTP level with httpx,
so it is straightforward to unit-test by mocking the token/userinfo calls. Each
provider exposes:

  * authorize_url(state, redirect_uri) - where to send the user's browser;
  * exchange_code(code, redirect_uri)  - swap the code for an access token;
  * fetch_profile(access_token)        - get (subject, email, name).

The backend owns the whole handshake and mints its own JWT at the end, so the
provider's tokens are never exposed to the browser or stored.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlencode

import httpx

from app.core.config import settings


@dataclass
class SocialProfile:
    provider: str
    subject: str          # the provider's stable unique user id
    email: str | None
    name: str | None


class OAuthProvider:
    name: str
    authorize_endpoint: str
    token_endpoint: str
    userinfo_endpoint: str
    scope: str

    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret

    @property
    def configured(self) -> bool:
        return bool(self.client_id and self.client_secret)

    def authorize_url(self, state: str, redirect_uri: str) -> str:
        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": self.scope,
            "state": state,
        }
        return f"{self.authorize_endpoint}?{urlencode(params)}"

    def exchange_code(self, code: str, redirect_uri: str) -> str:
        data = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code",
        }
        resp = httpx.post(
            self.token_endpoint,
            data=data,
            headers={"Accept": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()["access_token"]

    def fetch_profile(self, access_token: str) -> SocialProfile:
        raise NotImplementedError


class GoogleProvider(OAuthProvider):
    name = "google"
    authorize_endpoint = "https://accounts.google.com/o/oauth2/v2/auth"
    token_endpoint = "https://oauth2.googleapis.com/token"
    userinfo_endpoint = "https://openidconnect.googleapis.com/v1/userinfo"
    scope = "openid email profile"

    def fetch_profile(self, access_token: str) -> SocialProfile:
        resp = httpx.get(
            self.userinfo_endpoint,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return SocialProfile(
            provider=self.name,
            subject=str(data["sub"]),
            email=data.get("email"),
            name=data.get("name"),
        )


class FacebookProvider(OAuthProvider):
    name = "facebook"
    authorize_endpoint = "https://www.facebook.com/v19.0/dialog/oauth"
    token_endpoint = "https://graph.facebook.com/v19.0/oauth/access_token"
    userinfo_endpoint = "https://graph.facebook.com/me"
    scope = "email public_profile"

    def fetch_profile(self, access_token: str) -> SocialProfile:
        resp = httpx.get(
            self.userinfo_endpoint,
            params={"fields": "id,name,email", "access_token": access_token},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return SocialProfile(
            provider=self.name,
            subject=str(data["id"]),
            email=data.get("email"),
            name=data.get("name"),
        )


def get_provider(name: str) -> OAuthProvider:
    if name == "google":
        return GoogleProvider(settings.google_client_id, settings.google_client_secret)
    if name == "facebook":
        return FacebookProvider(settings.facebook_client_id, settings.facebook_client_secret)
    raise KeyError(name)
