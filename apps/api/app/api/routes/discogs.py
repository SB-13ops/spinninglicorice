from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_account_read, require_account_write
from app.core.oauth_state import get_oauth_state_store
from app.core.token_crypto import encrypt_token
from app.db.deps import get_db
from app.models.core import ExternalAccount, User
from app.services.discogs_client import DiscogsClient, client_for_account
from app.services.discogs_sync import DiscogsSyncService

router = APIRouter(prefix="/integrations/discogs", tags=["discogs"])


@router.get("/status")
def discogs_status(
    ctx = Depends(require_account_read),
    db: Session = Depends(get_db),
):
    account = db.scalar(
        select(ExternalAccount).where(
            ExternalAccount.user_id == ctx.owner_id,
            ExternalAccount.provider == "discogs",
        )
    )
    return {
        "connected": account is not None,
        "username": account.username if account else None,
        "last_synced_at": account.last_synced_at if account else None,
    }


@router.get("/connect")
def discogs_connect(ctx = Depends(require_account_read)):
    """Begin the Discogs OAuth flow. Only an account owner may connect their
    own Discogs identity (you cannot attach your Discogs to someone else's
    shared account)."""
    if not ctx.is_owner:
        raise HTTPException(status_code=403, detail="Only the account owner can connect Discogs.")
    oauth = DiscogsClient().begin_oauth()
    get_oauth_state_store().put(oauth.token, oauth.token_secret, str(ctx.owner_id))
    return {
        "authorization_url": oauth.authorization_url,
        "oauth_token": oauth.token,
    }


@router.get("/callback")
def discogs_callback(
    oauth_token: str = Query(...),
    oauth_verifier: str = Query(...),
    db: Session = Depends(get_db),
):
    """OAuth callback hit by Discogs' browser redirect.

    This endpoint is intentionally NOT protected by get_current_user: it is a
    top-level browser navigation from Discogs and carries no Authorization
    header. The initiating user is recovered from the pending-OAuth state that
    /connect stored, which is why that state includes the user id.
    """
    pending = get_oauth_state_store().pop(oauth_token)
    if not pending:
        raise HTTPException(status_code=400, detail="OAuth request token is missing or expired.")
    request_secret, user_id = pending

    user = db.get(User, UUID(user_id))
    if user is None:
        raise HTTPException(status_code=400, detail="Initiating user no longer exists.")

    token = DiscogsClient().finish_oauth(
        request_token=oauth_token,
        request_token_secret=request_secret,
        verifier=oauth_verifier,
    )

    client = DiscogsClient(
        access_token=token.token,
        access_token_secret=token.token_secret,
    )
    identity = client.identity()

    account = db.scalar(
        select(ExternalAccount).where(
            ExternalAccount.user_id == user.id,
            ExternalAccount.provider == "discogs",
        )
    )
    if account is None:
        account = ExternalAccount(user_id=user.id, provider="discogs")
        db.add(account)

    account.external_user_id = str(identity.get("id")) if identity.get("id") is not None else None
    account.username = identity.get("username")
    # Tokens are encrypted at rest with Fernet (key from TOKEN_ENCRYPTION_KEY).
    account.access_token_encrypted = encrypt_token(token.token)
    account.refresh_token_encrypted = encrypt_token(token.token_secret)
    account.sync_enabled = True
    db.commit()

    return {
        "connected": True,
        "username": account.username,
        "message": "Discogs connected. You can now run /sync.",
    }


@router.post("/sync")
def discogs_sync(
    ctx = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    account = db.scalar(
        select(ExternalAccount).where(
            ExternalAccount.user_id == ctx.owner_id,
            ExternalAccount.provider == "discogs",
        )
    )
    if not account or not account.username:
        raise HTTPException(status_code=400, detail="Connect Discogs first.")

    try:
        client = client_for_account(account)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    service = DiscogsSyncService(db, client)
    stats = service.sync_collection_and_wantlist(
        user_id=ctx.owner_id,
        username=account.username,
    )

    from datetime import datetime, timezone
    account.last_synced_at = datetime.now(timezone.utc)
    db.commit()

    return {"status": "complete", "stats": stats}
