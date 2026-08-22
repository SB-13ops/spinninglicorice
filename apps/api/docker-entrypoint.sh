#!/usr/bin/env sh
set -e

# Apply database migrations before serving traffic. `alembic upgrade head` is
# idempotent — if the database is already at head it is a no-op — so this is
# safe to run on every container start.
#
# NOTE on multiple replicas: if you scale this service beyond one instance,
# move migrations out of the start path (run them as a separate Railway
# pre-deploy / one-off command) so two replicas don't race on the first deploy.
# Alembic takes a transactional lock per migration, but a dedicated migration
# step is cleaner at scale.
echo "[entrypoint] Running database migrations (alembic upgrade head)..."
alembic upgrade head

# Bind to the port Railway provides (falls back to 8000 locally).
: "${PORT:=8000}"
echo "[entrypoint] Starting Uvicorn on 0.0.0.0:${PORT}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}"
