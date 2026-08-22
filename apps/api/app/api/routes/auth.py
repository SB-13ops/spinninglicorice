"""Authentication routes: register, login, and current-user lookup."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.db.deps import get_db
from app.models.core import User
from app.schemas.auth import RegisterRequest, TokenResponse, UserOut
from app.schemas.social import PaymentHandles

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Create a new user account and return an access token."""
    email = payload.email.lower().strip()
    existing = db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists.",
        )
    user = User(
        email=email,
        display_name=payload.display_name,
        hashed_password=hash_password(payload.password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Exchange email + password for an access token.

    Uses the OAuth2 password form (fields ``username`` and ``password``) so the
    interactive API docs' Authorize button works out of the box; ``username``
    carries the email.
    """
    email = form_data.username.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    # Verify against the stored hash. We run verify_password even when the user
    # is missing (against a throwaway value) is unnecessary here; a simple guard
    # is fine and the generic error avoids leaking which emails are registered.
    if (
        user is None
        or user.hashed_password is None
        or not verify_password(form_data.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    token = create_access_token(subject=user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return UserOut(
        id=str(current_user.id),
        email=current_user.email,
        display_name=current_user.display_name,
    )


@router.put("/me/payment-handles")
def set_payment_handles(
    payload: "PaymentHandles",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Set the user's Venmo/PayPal handles for off-app swap/sale settlement."""
    current_user.venmo_handle = payload.venmo_handle
    current_user.paypal_handle = payload.paypal_handle
    db.commit()
    return {
        "venmo_handle": current_user.venmo_handle,
        "paypal_handle": current_user.paypal_handle,
    }


# ---------------------------------------------------------------------------
# Social login (Google / Facebook)
# ---------------------------------------------------------------------------
import secrets as _secrets  # noqa: E402

from fastapi import Request  # noqa: E402
from fastapi.responses import RedirectResponse  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.oauth_state import get_login_state_store  # noqa: E402
from app.services.oauth_providers import get_provider  # noqa: E402
from app.services.social_auth import find_or_create_user  # noqa: E402


def _redirect_uri(provider: str) -> str:
    return f"{settings.api_base_url.rstrip('/')}/api/v1/auth/{provider}/callback"


@router.get("/{provider}/login")
def social_login(provider: str, redirect_path: str = "/"):
    """Begin social login: redirect the user's browser to the provider.

    `redirect_path` is where the web app should land after login (kept relative
    to the web app for safety).
    """
    if provider not in ("google", "facebook"):
        raise HTTPException(status_code=404, detail="Unknown provider.")
    p = get_provider(provider)
    if not p.configured:
        raise HTTPException(
            status_code=503,
            detail=f"{provider.title()} login is not configured on this server.",
        )
    if not redirect_path.startswith("/"):
        redirect_path = "/"
    state = _secrets.token_urlsafe(24)
    get_login_state_store().put(state, redirect_path)
    return RedirectResponse(url=p.authorize_url(state, _redirect_uri(provider)))


@router.get("/{provider}/callback")
def social_callback(
    provider: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    """Provider redirect target. Validates state, exchanges the code, resolves
    the user, mints our JWT, and bounces back to the web app with the token."""
    if provider not in ("google", "facebook"):
        raise HTTPException(status_code=404, detail="Unknown provider.")

    web = settings.web_base_url.rstrip("/")
    if error:
        return RedirectResponse(url=f"{web}/login?error=access_denied")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state.")

    redirect_path = get_login_state_store().pop(state)
    if redirect_path is None:
        # Unknown/expired state -> possible CSRF or a stale link.
        raise HTTPException(status_code=400, detail="Invalid or expired login state.")

    p = get_provider(provider)
    try:
        access_token = p.exchange_code(code, _redirect_uri(provider))
        profile = p.fetch_profile(access_token)
    except Exception:
        return RedirectResponse(url=f"{web}/login?error=provider_error")

    user = find_or_create_user(db, profile)
    if not user.is_active:
        return RedirectResponse(url=f"{web}/login?error=inactive")

    token = create_access_token(subject=user.id)
    # Hand the token to the web app via the URL fragment; the login page reads
    # it and stores it. (Fragment isn't sent to servers / logged in referers.)
    sep = "" if redirect_path.startswith("/") else "/"
    return RedirectResponse(url=f"{web}/login/callback#token={token}&next={sep}{redirect_path}")
