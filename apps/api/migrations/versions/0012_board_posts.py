"""public board posts and comments

The BoardPost / BoardPostComment models shipped without a migration, so on any
database built with `alembic upgrade head` every /board request failed with a
missing-table error.

Revision ID: 0012_board_posts
Revises: 0011_spinninglicorice_score
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0012_board_posts"
down_revision: Union[str, None] = "0011_spinninglicorice_score"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "board_posts",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("collection_item_id", sa.UUID(), nullable=True),
        sa.Column("wantlist_item_id", sa.UUID(), nullable=True),
        sa.Column("release_id", sa.UUID(), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="open", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["collection_item_id"], ["collection_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["wantlist_item_id"], ["wantlist_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["release_id"], ["releases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "collection_item_id", name="uq_board_post_collection_item"),
        sa.UniqueConstraint("user_id", "wantlist_item_id", name="uq_board_post_wantlist_item"),
    )
    op.create_index(op.f("ix_board_posts_user_id"), "board_posts", ["user_id"], unique=False)
    op.create_index(op.f("ix_board_posts_release_id"), "board_posts", ["release_id"], unique=False)
    op.create_index(op.f("ix_board_posts_created_at"), "board_posts", ["created_at"], unique=False)

    op.create_table(
        "board_post_comments",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("post_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["post_id"], ["board_posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_board_post_comments_post_id"), "board_post_comments", ["post_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_board_post_comments_post_id"), table_name="board_post_comments")
    op.drop_table("board_post_comments")
    op.drop_index(op.f("ix_board_posts_created_at"), table_name="board_posts")
    op.drop_index(op.f("ix_board_posts_release_id"), table_name="board_posts")
    op.drop_index(op.f("ix_board_posts_user_id"), table_name="board_posts")
    op.drop_table("board_posts")
