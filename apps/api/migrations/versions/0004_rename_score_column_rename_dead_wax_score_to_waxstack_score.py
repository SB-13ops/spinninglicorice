"""rename dead_wax_score to spinninglicorice_score

Revision ID: 0004_rename_score_column
Revises: 0003_user_auth_fields
Create Date: 2026-08-20

Product rename (Dead Wax -> SpinningLicorice). This renames the hunt_results score
column in place with ALTER ... RENAME COLUMN, preserving all existing values.

NOTE: autogenerate proposed add_column + drop_column, which would have DROPPED
every existing score. That was replaced with a rename so no data is lost.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0004_rename_score_column"
down_revision: Union[str, None] = "0003_user_auth_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column("hunt_results", "dead_wax_score", new_column_name="spinninglicorice_score")


def downgrade() -> None:
    op.alter_column("hunt_results", "spinninglicorice_score", new_column_name="dead_wax_score")
