"""Rename spinninglicorice_score → spinninglicorice_score (data-preserving).

The SpinningLicorice rebrand. This ALTERs the column name without touching
data, mirroring the waxstack_score → spinninglicorice_score rename.
"""
from alembic import op

revision = "0011_spinninglicorice_score"
down_revision = "0010_rename_score_spinninglicorice"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("hunt_results", "spinninglicorice_score", new_column_name="spinninglicorice_score")


def downgrade() -> None:
    op.alter_column("hunt_results", "spinninglicorice_score", new_column_name="spinninglicorice_score")
