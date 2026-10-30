from urllib.parse import parse_qs, urlparse

import pytest
from sqlalchemy import select

from app.api.routes import auth as auth_routes
from app.core.config import settings
from app.models.core import User
from app.services.oauth_providers import SocialProfile
from app.services.social_auth import EmailInUseError, find_or_create_user

from .conftest import register


def _profile(email, verified, subject="g-1"):
    return SocialProfile(provider="google", subject=subject, email=email, name="Real Owner", email_verified=verified)


def test_unverified_email_cannot_take_over_existing_account(client, db):
    register(client, "victim@example.com")
    with pytest.raises(EmailInUseError):
        find_or_create_user(db, _profile("victim@example.com", verified=False))


def test_verified_link_drops_squatters_password(client, db):
    # Someone registers with an address they don't own...
    register(client, "owner@example.com", password="squatter-pass")
    # ...then the real owner signs in with Google, which verifies the email.
    user = find_or_create_user(db, _profile("owner@example.com", verified=True))
    assert user.hashed_password is None
    login = client.post(
        "/api/v1/auth/login", data={"username": "owner@example.com", "password": "squatter-pass"}
    )
    assert login.status_code == 401


def test_new_social_user_is_created(db):
    user = find_or_create_user(db, _profile("new@example.com", verified=False))
    assert db.scalar(select(User).where(User.id == user.id)).email == "new@example.com"
    # The same identity resolves to the same user next time.
    assert find_or_create_user(db, _profile("new@example.com", verified=False)).id == user.id


class _FakeGoogle:
    configured = True

    def authorize_url(self, state, redirect_uri):
        return f"https://accounts.example/auth?state={state}"

    def exchange_code(self, code, redirect_uri):
        return "provider-token"

    def fetch_profile(self, access_token):
        return _profile("someone@example.com", verified=True)


@pytest.mark.parametrize("redirect_path", ["//evil.example", "/\\evil.example", "https://evil.example", "/collection"])
def test_login_redirect_stays_on_web_app(client, monkeypatch, redirect_path):
    monkeypatch.setattr(auth_routes, "get_provider", lambda name: _FakeGoogle())
    start = client.get(
        "/api/v1/auth/google/login", params={"redirect_path": redirect_path}, follow_redirects=False
    )
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]

    done = client.get(
        "/api/v1/auth/google/callback", params={"code": "c", "state": state}, follow_redirects=False
    )
    location = done.headers["location"]
    assert location.startswith(f"{settings.web_base_url}/login/callback#")
    fragment = parse_qs(urlparse(location).fragment)
    assert fragment["token"]
    assert fragment["next"] == ["/collection" if redirect_path == "/collection" else "/"]


def test_callback_reports_unverified_email_collision(client, monkeypatch):
    register(client, "taken@example.com")

    class _Unverified(_FakeGoogle):
        def fetch_profile(self, access_token):
            return _profile("taken@example.com", verified=False, subject="g-2")

    monkeypatch.setattr(auth_routes, "get_provider", lambda name: _Unverified())
    start = client.get("/api/v1/auth/google/login", follow_redirects=False)
    state = parse_qs(urlparse(start.headers["location"]).query)["state"][0]
    done = client.get(
        "/api/v1/auth/google/callback", params={"code": "c", "state": state}, follow_redirects=False
    )
    assert done.headers["location"].endswith("/login?error=email_in_use")
