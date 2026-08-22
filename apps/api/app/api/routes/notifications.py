from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_account_read, require_account_write
from app.db.deps import get_db
from app.models.core import Notification, User
from app.services.automation_service import AutomationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("/refresh")
def refresh_notifications(
    ctx = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    service = AutomationService(db, db.get(User, ctx.owner_id))
    created = service.generate_hunter_notifications() + service.generate_scout_notifications()
    return {"created": created}


@router.get("")
def list_notifications(
    ctx = Depends(require_account_read),
    db: Session = Depends(get_db),
):
    rows = db.execute(
        select(Notification)
        .where(Notification.user_id == ctx.owner_id)
        .order_by(Notification.created_at.desc())
        .limit(30)
    ).scalars().all()
    return {
        "items": [
            {
                "id": str(n.id),
                "type": n.notification_type,
                "title": n.title,
                "body": n.body,
                "payload": n.payload,
                "read": n.read_at is not None,
                "created_at": str(n.created_at),
            }
            for n in rows
        ]
    }
