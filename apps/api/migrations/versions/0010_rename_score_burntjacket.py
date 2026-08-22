"""Rename waxstack_score -> spinninglicorice_score (in place, data-preserving).

Part of the SpinningLicorice rebrand. This ALTERs the column name without touching
data, mirroring the earlier dead_wax_score -> waxstack_score rename.
"""
from alembic import op

revision = "0010_rename_score_spinninglicorice"
down_revision = "0009_value_tracking"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("hunt_results", "waxstack_score", new_column_name="spinninglicorice_score")


def downgrade() -> None:
    op.alter_column("hunt_results", "spinninglicorice_score", new_column_name="waxstack_score")
