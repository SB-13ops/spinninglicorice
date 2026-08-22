# syntax=docker/dockerfile:1
# WaxStack API image (FastAPI + Uvicorn).
#
# Build context is apps/api/ — on Railway set this service's Root Directory to
# apps/api and Railway will build with this Dockerfile automatically.

FROM python:3.12-slim AS base

# - PYTHONUNBUFFERED: log lines flush immediately (visible in Railway logs)
# - PIP_NO_CACHE_DIR: smaller image
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install dependencies first so the layer is cached when only app code changes.
# psycopg[binary], cryptography, pwdlib[bcrypt] all ship manylinux wheels, so no
# system build toolchain is required on python:3.12-slim.
COPY requirements.txt ./
RUN pip install -r requirements.txt

# Copy the application, migrations, and Alembic config.
COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./alembic.ini
COPY docker-entrypoint.sh ./docker-entrypoint.sh
RUN chmod +x ./docker-entrypoint.sh

# Run as a non-root user.
RUN useradd --create-home --uid 10001 appuser \
    && chown -R appuser:appuser /app
USER appuser

# Railway injects $PORT at runtime; default to 8000 for local `docker run`.
ENV PORT=8000
EXPOSE 8000

# The entrypoint applies database migrations, then starts Uvicorn on $PORT.
ENTRYPOINT ["./docker-entrypoint.sh"]
