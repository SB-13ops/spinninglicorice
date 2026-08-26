"""Ensure the score column is named spinninglicorice_score (idempotent).

Guarded the same way as 0010: only acts if a column literally named
"burntjacket_score" still exists. Safe no-op otherwise.
"""
from alembic import op
from sqlalchemy import inspect

revision = "0011_spinninglicorice_score"
down_revision = "0010_score_spinninglicorice"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    insp = inspect(op.get_bind())
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    cols = _columns("hunt_results")
    if "burntjacket_score" in cols and "spinninglicorice_score" not in cols:
        op.alter_column("hunt_results", "burntjacket_score", new_column_name="spinninglicorice_score")


def downgrade() -> None:
    cols = _columns("hunt_results")
    if "spinninglicorice_score" in cols and "burntjacket_score" not in cols:
        op.alter_column("hunt_results", "spinninglicorice_score", new_column_name="burntjacket_score")
