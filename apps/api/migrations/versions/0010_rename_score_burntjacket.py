"""Rename waxstack_score -> spinninglicorice_score (data-preserving, idempotent).

Guarded: only renames if a column literally named "waxstack_score" still
exists. On environments where 0004 already produced the final column name
directly (nothing to do here) this is a safe no-op, so the chain works
whether replayed from empty or continued from a partially-applied database.
"""
from alembic import op
from sqlalchemy import inspect

revision = "0010_score_spinninglicorice"
down_revision = "0009_value_tracking"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    insp = inspect(op.get_bind())
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    cols = _columns("hunt_results")
    if "waxstack_score" in cols and "spinninglicorice_score" not in cols:
        op.alter_column("hunt_results", "waxstack_score", new_column_name="spinninglicorice_score")


def downgrade() -> None:
    cols = _columns("hunt_results")
    if "spinninglicorice_score" in cols and "waxstack_score" not in cols:
        op.alter_column("hunt_results", "spinninglicorice_score", new_column_name="waxstack_score")
