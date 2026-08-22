# Deploying SpinningLicorice: GitHub → Railway (complete, current)

Start-to-finish steps to get SpinningLicorice live on Railway. Current as of the full
build — auth, sharing, social login, home personalization, groups, AI, trip
planner, affiliate links, collection insights, add/rate records, barcode
scanning, and wantlist.

Companion docs: `RAILWAY_VARIABLES.md` (every env var), `PRE_LAUNCH_CHECKLIST.md`
(post-deploy verification), `BUILD_SUMMARY.md` (what's built).

SpinningLicorice runs as **four Railway components in one project**: a **PostgreSQL**
plugin, a **Redis** plugin, an **API** service (`apps/api`), and a **web**
service (`apps/web`). Both app services build from their own Dockerfile, which
Railway auto-detects once you set each service's Root Directory.

---

## Part A — Push the code to GitHub

### 1. Create the repository
- GitHub -> **New repository** -> name it `spinninglicorice` -> **Private** is fine ->
  do **not** add a README/.gitignore (the project already has files). Copy the
  repo URL.

### 2. Confirm secrets won't be committed
The project ships a `.env.example` (placeholders only). Make sure a real `.env`
never gets committed. Verify there's a root `.gitignore` containing at least:

```
.env
.env.*
!.env.example
__pycache__/
*.pyc
.venv/
node_modules/
.next/
```

### 3. Initialize and push (from the unzipped project root)
```bash
cd spinninglicorice            # contains apps/, docs/
git init
git add .
git commit -m "SpinningLicorice: initial commit"
git branch -M main
git remote add origin https://github.com/<you>/spinninglicorice.git
git push -u origin main
```

> If you ever accidentally commit a real `.env`: `git rm --cached .env`, commit,
> and **rotate** any exposed secret.

---

## Part B — Create the Railway project + data plugins

1. Railway -> **New Project** -> **Deploy from GitHub repo** -> pick `spinninglicorice`
   -> authorize if prompted.
2. **+ New -> Database -> PostgreSQL.** (Its image includes pgvector; migration
   `0001` enables the extension automatically.)
3. **+ New -> Database -> Redis.** (Used for OAuth state + the Discogs response
   cache.)

---

## Part C — Configure and deploy the API service

1. Open the service Railway created from the repo (or **+ New -> GitHub Repo**
   -> same repo). This is the **API**.
2. **Settings -> Root Directory:** `apps/api`
   - Railway auto-detects `apps/api/Dockerfile` and `apps/api/railway.json`
     (which sets the `/api/v1/health` healthcheck).
3. **Variables ->** add at minimum (full list in `RAILWAY_VARIABLES.md`):
   ```
   APP_ENV=production
   DATABASE_URL=${{Postgres.DATABASE_URL}}
   REDIS_URL=${{Redis.REDIS_URL}}
   JWT_SECRET_KEY=<generated>
   TOKEN_ENCRYPTION_KEY=<generated>
   DISCOGS_OAUTH_TEMP_SECRET=<generated>
   API_BASE_URL=https://<your-api-domain>
   WEB_BASE_URL=https://<your-web-domain>
   CORS_ALLOW_ORIGINS=https://<your-web-domain>
   ```
   Generate the three secrets:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(48))"
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
   > The API **refuses to boot in production** if `JWT_SECRET_KEY`,
   > `TOKEN_ENCRYPTION_KEY`, or `DISCOGS_OAUTH_TEMP_SECRET` are missing or left
   > at dev defaults. Intentional — a clear startup error, not a silent insecure
   > boot.
4. **Deploy.** This is the **first real Docker build** — watch the build logs.
   On start you should see, in order:
   ```
   [entrypoint] Running database migrations (alembic upgrade head)...
   ... 9 migrations run ...
   [entrypoint] Starting Uvicorn on 0.0.0.0:$PORT
   ```
5. **Settings -> Networking -> Generate Domain.** Note the API domain, then set
   `API_BASE_URL` to it and redeploy if it changed.

---

## Part D — Configure and deploy the web service

1. **+ New -> GitHub Repo** -> same repo (a second service).
2. **Settings -> Root Directory:** `apps/web`
3. **Variables:**
   ```
   NEXT_PUBLIC_API_BASE_URL=https://<your-api-domain>/api/v1
   ```
   > WARNING: compiled in at **build time**. If you change it later you must
   > **redeploy** the web service — a restart won't pick it up.
4. **Deploy**, then **Generate Domain**. Note the web domain.

---

## Part E — Wire the two services together

On the **API** service, set/confirm these to the real web domain and redeploy:
```
WEB_BASE_URL=https://<your-web-domain>
CORS_ALLOW_ORIGINS=https://<your-web-domain>
```

At this point SpinningLicorice is live for email/password accounts: register, log in,
add records by hand, rate them, use the collection/wantlist toggle, view
insights (value, completion, collector card), and share. Features needing
third-party credentials stay gracefully off until you add them (next).

---

## Part F — Add third-party integrations (each optional, independent)

Add these whenever ready; each unlocks a feature and degrades cleanly when
absent. Redirect/callback URIs must point at your **API** domain.

- **Discogs** (sync, Hunter, search-to-add, barcode scan):
  `DISCOGS_CONSUMER_KEY`, `DISCOGS_CONSUMER_SECRET`,
  `DISCOGS_CALLBACK_URL=https://<api>/api/v1/integrations/discogs/callback`
- **Google login:** `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
  (redirect `https://<api>/api/v1/auth/google/callback`)
- **Facebook login:** `FACEBOOK_CLIENT_ID`, `FACEBOOK_CLIENT_SECRET`
  (redirect `https://<api>/api/v1/auth/facebook/callback`)
- **Anthropic AI** (NL hunt parse, enrichment, trip estimates):
  `ANTHROPIC_API_KEY` (+ optional `AI_FAST_MODEL`, `AI_RESEARCH_MODEL`,
  `AI_WEB_SEARCH_MAX_USES`)
- **Trip planner / affiliate revenue** (all optional): `EXPEDIA_AFFILIATE_ID`,
  `DEFAULT_GAS_PRICE_USD`, `TICKET_AFFILIATE_PROVIDER`/`TICKET_AFFILIATE_ID`,
  `CAR_AFFILIATE_PROVIDER`/`CAR_AFFILIATE_ID`,
  `RIDESHARE_PROVIDER`/`RIDESHARE_REFERRAL_URL`

See `RAILWAY_VARIABLES.md` for the full table and notes.

---

## Part G — Verify the deploy

Run the included smoke test against the live API:
```bash
pip install httpx
python scripts/smoke_test.py --base-url https://<your-api-domain>
```
Expect all checks **PASS** (exit 0): health, register, login, JWT, protected
routes, home feed, hunt create, NL parse, group create, insights value +
completion, and auth enforcement. `ai/status` shows a warning (not a failure)
until you set `ANTHROPIC_API_KEY`.

Then work through `PRE_LAUNCH_CHECKLIST.md` for the by-hand checks that need a
browser or real APIs.

---

## Redeploying after changes
Railway auto-deploys on push to `main`:
```bash
git add . && git commit -m "your change" && git push
```
Reminders: changing `NEXT_PUBLIC_API_BASE_URL` requires a web **redeploy** (it's
compiled in); API secret changes just need an API restart/redeploy.

---

## Troubleshooting the first deploy

- **API crashes with "Insecure configuration for production"** — the intended
  fail-fast. Set real `JWT_SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, and
  `DISCOGS_OAUTH_TEMP_SECRET`.
- **Web loads but API calls fail / CORS error** — `CORS_ALLOW_ORIGINS` on the
  API must exactly match the web domain, and `NEXT_PUBLIC_API_BASE_URL` on the
  web must be `https://<api>/api/v1`. Redeploy web after changing the latter.
- **Migrations didn't run** — check API deploy logs for the
  `[entrypoint] Running database migrations` line; if the DB is unreachable,
  confirm `DATABASE_URL=${{Postgres.DATABASE_URL}}` resolved.
- **Social login fails** — the provider console's redirect URI must exactly
  equal `https://<api>/api/v1/auth/<provider>/callback`.
- **Discogs search / barcode scan returns "connect Discogs first"** — expected
  until a Discogs account is connected in the app; connect + sync, then retry.
- **Barcode camera doesn't open** — the live camera needs HTTPS (Railway domains
  are HTTPS) and camera permission; the photo-upload fallback also works.
