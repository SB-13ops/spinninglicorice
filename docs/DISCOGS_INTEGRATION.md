# Discogs Integration — V1

## What is implemented

The API now includes the first real Discogs path:

1. `GET /api/v1/integrations/discogs/connect`
2. Open the returned `authorization_url`
3. Authorize Burnt Jacket in Discogs
4. Discogs redirects to `/api/v1/integrations/discogs/callback`
5. Burnt Jacket exchanges the OAuth verifier for an access token
6. `POST /api/v1/integrations/discogs/sync`
7. Collection folder `0` and Wantlist are paged through
8. Releases are normalized into Burnt Jacket `albums`, `releases`, `artists`, mappings, collection items and wantlist items
9. `GET /api/v1/collection` returns the imported collection

## Local setup

Create a Discogs application and put its consumer key and secret into `.env`:

```env
DISCOGS_CONSUMER_KEY=...
DISCOGS_CONSUMER_SECRET=...
DISCOGS_CALLBACK_URL=http://localhost:8000/api/v1/integrations/discogs/callback
```

Start PostgreSQL and the API, then create local tables:

```bash
# Create the schema with Alembic (run from apps/api/ with your venv active):
alembic upgrade head
```

Start the OAuth flow:

```bash
curl http://localhost:8000/api/v1/integrations/discogs/connect
```

Open the returned authorization URL in a browser.

After successful callback, run:

```bash
curl -X POST http://localhost:8000/api/v1/integrations/discogs/sync
```

View collection:

```bash
curl http://localhost:8000/api/v1/collection
```

## Production hardening still required

- Replace the demo-user shortcut with managed authentication.
- Encrypt provider tokens at rest.
- Replace in-memory pending OAuth secrets with encrypted server-side sessions or Redis.
- Add sync-job/background-worker execution.
- Handle API rate limits and retries explicitly.
- Add detailed Discogs custom-field/condition mapping.
- Improve album/master normalization so multiple pressings share the same Burnt Jacket album.
- Add supported Discogs write-back operations.
