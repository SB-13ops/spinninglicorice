from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import require_account_read, require_account_write
from app.db.deps import get_db
from app.models.core import User
from app.services.collector_dna import CollectorDNAService

router = APIRouter(prefix="/dna", tags=["collector-dna"])


@router.get("")
def get_dna(
    ctx = Depends(require_account_read),
    db: Session = Depends(get_db),
):
    return CollectorDNAService(db).get(user_id=ctx.owner_id)


@router.post("/rebuild")
def rebuild_dna(
    ctx = Depends(require_account_write),
    db: Session = Depends(get_db),
):
    return CollectorDNAService(db).rebuild(user_id=ctx.owner_id)
