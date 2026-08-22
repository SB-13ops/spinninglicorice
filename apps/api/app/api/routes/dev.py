"""Development-only routes.

This router is only mounted when APP_ENV == "development" (see app/main.py),
so nothing here is reachable on a production deployment.

The previous POST /dev/bootstrap-db endpoint (which called
Base.metadata.create_all) has been removed: the database schema is now owned
by Alembic migrations. Create/upgrade the schema with:

    alembic upgrade head

create_all() only ever ADDS missing tables — it never alters existing ones —
so it silently diverges from the models over time and must not be used to
manage a real schema.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.deps import get_db

router = APIRouter(prefix="/dev", tags=["development"])


@router.get("/db-revision")
def db_revision(db: Session = Depends(get_db)):
    """Report the Alembic migration revision the database is currently on.

    Handy for confirming a deploy actually ran `alembic upgrade head`.
    Read-only; makes no schema changes.
    """
    try:
        row = db.execute(text("SELECT version_num FROM alembic_version")).first()
        return {"alembic_revision": row[0] if row else None}
    except Exception:
        # alembic_version won't exist until the first migration has run.
        return {"alembic_revision": None, "note": "No migrations applied yet."}
