from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import (
    auth,
    collection,
    discogs,
    dna,
    health,
    home,
    home_feature,
    hunter,
    notifications,
    public,
    scout,
    sharing,
    groups,
    group_messages,
    group_listings,
    ai,
    trips,
    insights,
)

app = FastAPI(title="Burnt Jacket API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(home.router, prefix="/api/v1")
app.include_router(home_feature.router, prefix="/api/v1")
app.include_router(collection.router, prefix="/api/v1")
app.include_router(hunter.router, prefix="/api/v1")
app.include_router(dna.router, prefix="/api/v1")
app.include_router(scout.router, prefix="/api/v1")
app.include_router(discogs.router, prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(sharing.router, prefix="/api/v1")
app.include_router(public.router, prefix="/api/v1")
app.include_router(groups.router, prefix="/api/v1")
app.include_router(group_messages.router, prefix="/api/v1")
app.include_router(group_listings.router, prefix="/api/v1")
app.include_router(ai.router, prefix="/api/v1")
app.include_router(trips.router, prefix="/api/v1")
app.include_router(insights.router, prefix="/api/v1")

# Development-only routes (schema diagnostics, etc.) are never mounted in
# production. The old unauthenticated /dev/bootstrap-db table creator is gone;
# the schema is owned by Alembic migrations.
if settings.app_env == "development":
    from app.api.routes import dev

    app.include_router(dev.router, prefix="/api/v1")
