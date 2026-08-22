# Deploying SpinningLicorice to Railway

SpinningLicorice deploys as **four Railway components in one project**:

| Component | What it is | Source |
|-----------|-----------|--------|
| Postgres  | Database plugin (must support pgvector) | Railway plugin |
| Redis     | Redis plugin (OAuth state, caching)     | Railway plugin |
| `spinninglicorice-api` | FastAPI service | `apps/api/Dockerfile` |
| `spinninglicorice-web` | Next.js service | `apps/web/Dockerfile` |

Both app services build from their own Dockerfile, selected automatically when
you set each service's **Root Directory** (see below). The API applies database
migrations on startup and binds to Railway's injected `$PORT`; the web service
serves Next.js standalone output.

---

## 1. Create the project and data plugins

1. Create a new Railway project from your GitHub repo.
2. Add a **PostgreSQL** plugin. SpinningLicorice uses pgvector — Railway's standard
   Postgres image includes the `vector` extension, and migration `0001` runs
   `CREATE EXTENSION IF NOT EXISTS vector` so it is enabled automatically on
   first `alembic upgrade head`. (If your Postgres image lacks pgvector, use a
   pgvector-enabled image instead.)
3. Add a **Redis** plugin.

Both plugins expose connection variables (`DATABASE_URL`, `REDIS_URL`) that you
will reference from the API service.

## 2. Create the API service (`spinninglicorice-api`)

1. New service → deploy from the same repo.
2. **Settings → Root Directory:** `apps/api`
   Railway then builds with `apps/api/Dockerfile` automatically (the committed
   `apps/api/railway.json` also pins the Dockerfile builder and the
   `/api/v1/health` healthcheck).
3. **Variables** (Settings → Variables):

   ```
   APP_ENV=production
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   JWT_SECRET_KEY=<generate: python -c "import secrets; print(secrets.token_urlsafe(48))">
   TOKEN_ENCRYPTION_KEY=<generate: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
   DISCOGS_OAUTH_TEMP_SECRET=<any strong random string>
   CORS_ALLOW_ORIGINS=https://<your-web-domain>
   DISCOGS_CONSUMER_KEY=...
   DISCOGS_CONSUMER_SECRET=...
   DISCOGS_CALLBACK_URL=https://<your-api-domain>/api/v1/integrations/discogs/callback
   TICKETMASTER_API_KEY=...
   ANTHROPIC_API_KEY=...          # used by the AI features (later step)
   ```

   The `${{Postgres.DATABASE_URL}}` / `${{Redis.REDIS_URL}}` syntax references
   the plugin variables — Railway wires them for you. `DATABASE_URL` arrives as
   `postgresql://...`; the app normalizes it to the psycopg driver form at
   runtime, so paste it as-is.

   > **The API will refuse to boot in production** if `JWT_SECRET_KEY`,
   > `TOKEN_ENCRYPTION_KEY`, or `DISCOGS_OAUTH_TEMP_SECRET` are missing or left
   > at their dev defaults. This is intentional — set real values.

4. Deploy. On start the container runs `alembic upgrade head` (creating the
   schema + extensions) and then Uvicorn. Watch the deploy logs for
   `[entrypoint] Running database migrations` followed by `Uvicorn running`.
5. **Generate a domain** (Settings → Networking) so the web app can reach it.

## 3. Create the web service (`spinninglicorice-web`)

1. New service → same repo.
2. **Settings → Root Directory:** `apps/web`
3. **Variable:**

   ```
   NEXT_PUBLIC_API_BASE_URL=https://<your-api-domain>/api/v1
   ```

   > **Important:** this is a `NEXT_PUBLIC_*` variable, so Next.js **inlines it
   > at build time**, not runtime. The Dockerfile reads it as a build arg.
   > Railway passes service variables to the build, so setting it here is
   > enough — but if you change it later you must **redeploy** (a restart alone
   > won't pick it up, because the value is baked into the client bundle).

4. Deploy, then **generate a domain**.
5. Back on the **API** service, make sure `CORS_ALLOW_ORIGINS` is set to this
   web domain (comma-separate if you have several), then redeploy the API.

## 4. Connect Discogs (per user, after deploy)

The Discogs OAuth callback URL registered with Discogs must match the API's
public domain: `https://<your-api-domain>/api/v1/integrations/discogs/callback`.
Update `DISCOGS_CALLBACK_URL` (API variable) and your Discogs app settings to
that URL.

---

## Scaling note (migrations + replicas)

The API applies migrations on container start. This is fine for a single
replica. **If you scale the API past one instance,** move migrations out of the
start path — run `alembic upgrade head` as a one-off / pre-deploy command
instead — so replicas don't race on the first deploy. `alembic upgrade head` is
idempotent, so restarts of a single replica are always safe.

## Local parity

`docker-compose.yml` at the repo root runs the same four components locally
(Postgres + Redis + API + web) so local dev matches this topology. See the
README for the non-Docker local workflow (uvicorn + `npm run dev`).

---

## Social login (Google / Facebook) setup

SpinningLicorice signs users in with Google and Facebook. You must create OAuth apps in
each provider's console and set the credentials as **API service** variables.

### Google
1. Google Cloud Console → APIs & Services → Credentials → *Create OAuth client ID* → **Web application**.
2. Authorized redirect URI: `https://<your-api-domain>/api/v1/auth/google/callback`
3. Copy the client ID / secret into API variables:
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ```

### Facebook
1. Facebook for Developers → *Create App* → add **Facebook Login**.
2. Valid OAuth Redirect URI: `https://<your-api-domain>/api/v1/auth/facebook/callback`
3. Copy the app ID / secret into API variables:
   ```
   FACEBOOK_CLIENT_ID=...
   FACEBOOK_CLIENT_SECRET=...
   ```

### Required supporting variables (API service)
```
API_BASE_URL=https://<your-api-domain>        # used to build the OAuth redirect_uri
WEB_BASE_URL=https://<your-web-domain>         # where users land after login, and for share links
```

The login flow: the web app sends users to `<API>/api/v1/auth/{provider}/login`,
the provider redirects back to the API callback, the API mints a SpinningLicorice JWT and
bounces the browser to `<WEB>/login/callback#token=...`, which the web app stores.
A provider that isn't configured returns 503 and its button simply won't work —
so you can ship with just Google first if you like.

## Account sharing

No setup needed — it's built in. Owners manage sharing at `/sharing` in the web
app: create viewer/admin invite links, manage members, and toggle an anonymous
public read-only link (`/shared/<token>`). Invite links are `/invite/<token>`.

## Friend groups (social layer)

Built in, no setup. Members create groups at `/groups`, invite via link
(`/groups/join/<token>`), chat on a polling message board, and post swap/sale
listings. Settlement is **off-app** — members add Venmo/PayPal handles (Profile),
and the app surfaces them to interested buyers. It never touches money.

Note on Facebook groups: Meta's API can't create or post to Groups, so SpinningLicorice
only stores a link to a group you manage on Facebook — it doesn't integrate one.

Real-time chat: the message board polls (every ~4s). It's structured so a
WebSocket transport can be added later without changing the data model.

## AI features (Anthropic / Claude)

Set `ANTHROPIC_API_KEY` on the API service to enable:
* **Natural-language hunt parsing** — Claude (Haiku) turns "early Bowie I don't
  own, VG+ under £40" into structured criteria far more reliably than the regex
  (which stays as an automatic fallback).
* **Concert Scout enrichment** and **pressing research** — these use Anthropic's
  server-side web search tool (billed ~$10/1,000 searches), so they're
  user-initiated only and capped by `AI_WEB_SEARCH_MAX_USES` (default 3).

Everything degrades gracefully: with no key, `/ai/status` reports disabled, the
enrichment buttons hide, hunt parsing uses the regex, and the app runs normally.
Models are configurable via `AI_FAST_MODEL` / `AI_RESEARCH_MODEL` — check
Anthropic's current model list, as model names change over time.
