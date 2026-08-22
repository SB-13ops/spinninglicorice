# spinninglicorice

WaxStack — a vinyl record collection app with Discogs sync, an AI-assisted
record hunter/scout, collection valuation, and a social sharing layer.

## Structure

- `apps/api` — FastAPI backend (SQLAlchemy, Alembic migrations, Postgres, Redis)
- `apps/web` — Next.js frontend
- `docs/` — architecture, deployment, and feature docs
- `scripts/smoke_test.py` — post-deploy smoke test against a live API

## Getting started

See `docs/ARCHITECTURE.md` for how the pieces fit together and
`docs/DEPLOY_RAILWAY.md` / `docs/DEPLOY_GITHUB_AND_RAILWAY.md` for deployment.
Copy `.env.example` to `.env` (and `apps/web/.env.local.example` to
`apps/web/.env.local`) and fill in credentials before running locally.

Before a production launch, work through `docs/PRE_LAUNCH_CHECKLIST.md`.
