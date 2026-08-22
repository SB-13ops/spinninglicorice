"""create required postgres extensions (vector, pgcrypto)

Revision ID: 0001_extensions
Revises:
Create Date: 2026-08-20

These extensions were previously created by infra/postgres/001_bootstrap.sql,
which only runs via the docker-compose initdb hook and therefore does NOT run
on a managed Postgres instance (Railway, etc.). Creating them here means a
fresh database provisioned anywhere gets them as part of `alembic upgrade head`.

* pgcrypto  - used for gen_random_uuid() and general crypto helpers.
* vector    - pgvector; the schema is "pgvector-ready" for future embedding
              columns. Requires the pgvector extension to be installed on the
              server (the production image is pgvector/pgvector:pg16).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_extensions"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Dropping shared extensions on downgrade is intentionally conservative:
    # other objects may depend on them. We drop only if unused.
    op.execute("DROP EXTENSION IF EXISTS vector")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
