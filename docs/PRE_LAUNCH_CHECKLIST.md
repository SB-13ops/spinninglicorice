# spinninglicorice Pre-Launch Checklist

Everything is code-complete and tested in development. This checklist covers the
steps only you can do — creating credentials, deploying, and smoke-testing the
paths that need real third-party services or a browser.

Work top to bottom. Each item says **why** it matters and **how** to verify it.

---

## 1. Create external credentials

You need four sets of credentials. None are baked into the code — they're all
environment variables.

- [ ] **Discogs** — consumer key + secret (for collection sync and Hunter).
  Register an app at https://www.discogs.com/settings/developers
  Callback URL: `https://<your-api-domain>/api/v1/integrations/discogs/callback`

- [ ] **Google OAuth** — client ID + secret (social login).
  Google Cloud Console → Credentials → OAuth client ID → Web application.
  Redirect URI: `https://<your-api-domain>/api/v1/auth/google/callback`

- [ ] **Facebook OAuth** — app ID + secret (social login).
  Facebook for Developers → your app → Facebook Login.
  Redirect URI: `https://<your-api-domain>/api/v1/auth/facebook/callback`

- [ ] **Anthropic** — API key (AI hunt parsing, enrichment). Optional — the app
  runs without it, AI features just stay off.

> Full console walkthroughs are in `docs/DEPLOY_RAILWAY.md`.

---

## 2. Generate secrets

These protect auth tokens and encrypted Discogs tokens. **The API refuses to
boot in production if these are missing or left at dev defaults** — that's
intentional.

- [ ] `JWT_SECRET_KEY` — `python -c "import secrets; print(secrets.token_urlsafe(48))"`
- [ ] `TOKEN_ENCRYPTION_KEY` — `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- [ ] `DISCOGS_OAUTH_TEMP_SECRET` — any strong random string.

---

## 3. Provision Railway infrastructure

- [ ] Create the Railway project from the repo.
- [ ] Add a **PostgreSQL** plugin (pgvector-capable — migration `0001` enables
  the `vector` extension automatically).
- [ ] Add a **Redis** plugin (OAuth state + Discogs response cache).
- [ ] Create the **API** service, Root Directory `apps/api`.
- [ ] Create the **web** service, Root Directory `apps/web`.

---

## 4. Set environment variables

**API service:**

- [ ] `APP_ENV=production`
- [ ] `DATABASE_URL=${{Postgres.DATABASE_URL}}`
- [ ] `REDIS_URL=${{Redis.REDIS_URL}}`
- [ ] `JWT_SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, `DISCOGS_OAUTH_TEMP_SECRET` (from step 2)
- [ ] `API_BASE_URL=https://<your-api-domain>`
- [ ] `WEB_BASE_URL=https://<your-web-domain>`
- [ ] `CORS_ALLOW_ORIGINS=https://<your-web-domain>`
- [ ] `DISCOGS_CONSUMER_KEY`, `DISCOGS_CONSUMER_SECRET`, `DISCOGS_CALLBACK_URL`
- [ ] `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
- [ ] `FACEBOOK_CLIENT_ID`, `FACEBOOK_CLIENT_SECRET`
- [ ] `ANTHROPIC_API_KEY` (optional), `AI_FAST_MODEL`, `AI_RESEARCH_MODEL`

**Web service:**

- [ ] `NEXT_PUBLIC_API_BASE_URL=https://<your-api-domain>/api/v1`
  > ⚠️ This is inlined at **build time**. If you change it later you must
  > **redeploy**, not just restart.

---

## 5. First deploy

- [ ] Deploy the **API**. This is the **first time the Docker image is built** —
  the Dockerfiles were written and their commands validated, but never
  `docker build`-ed in development. **Watch the build logs.**
- [ ] In the API deploy logs, confirm:
  `[entrypoint] Running database migrations` → all 8 migrations run → `Uvicorn running`.
- [ ] Generate a public domain for the API (Settings → Networking).
- [ ] Deploy the **web** service; generate its domain.
- [ ] Update the API's `CORS_ALLOW_ORIGINS` and `WEB_BASE_URL` to the real web
  domain, and redeploy the API if they changed.

---

## 6. Smoke test the API

Run the included script against the deployed API:

```bash
pip install httpx
python scripts/smoke_test.py --base-url https://<your-api-domain>
```

- [ ] All checks **PASS** (exit code 0). It verifies health, register, login,
  the JWT, protected routes, home feed, hunt create, NL parse, group create,
  and that unauthenticated requests are rejected.
- [ ] `ai/status` shows **ENABLED** if you set `ANTHROPIC_API_KEY` (it warns,
  not fails, when AI is off).

---

## 7. Smoke test the paths that need a browser / real APIs

These couldn't be exercised in development (they need real credentials or a
browser), so verify them by hand on the live site:

- [ ] **Google login** — click through the real consent screen; land back
  signed in. Confirm a user + `oauth_identity` row is created.
- [ ] **Facebook login** — same.
- [ ] **Discogs connect + sync** — connect an account, run a sync, confirm
  records appear in the collection.
- [ ] **A real Hunter run** — create a hunt and refresh it. Watch the API logs
  for Discogs `429` rate-limit warnings; the client backs off and retries, but
  confirm the behavior looks sane against the live API.
- [ ] **AI hunt parse** (if AI enabled) — a natural-language query returns
  sensible structured criteria.
- [ ] **AI enrichment** (if AI enabled) — "Research this pressing" returns text
  with source citations. This makes a real (billed) web search.
- [ ] **UI click-through** — the frontend was build- and type-checked but not
  clicked in a browser here. Walk: login → home (personalize the hero) →
  collection → sharing (create an invite, toggle the public link, open it in a
  private window) → groups (create, post a message, list a record).
- [ ] **AI disclosure** appears at the bottom of every page, including the login
  page and the public shared view.

---

## 8. Post-launch sanity

- [ ] Confirm the anonymous public share link works logged-out, and that
  toggling it off returns 404.
- [ ] Confirm a viewer (shared account, read-only) cannot write.
- [ ] Set a low-priority reminder to watch Anthropic + Discogs usage for the
  first week (AI web searches and Discogs calls both have real costs/limits).

---


## 7b. Verify the newer features (post-deploy, in the browser)

- [ ] **Add a record by hand** — Collection -> + ADD RECORD -> "Type it in";
  add a title/artist, set a star rating, save; confirm it appears with the
  rating.
- [ ] **Collection vs. wantlist toggle** — add one record to the wantlist (with
  a max price) and confirm it lands on the wantlist, not the collection.
- [ ] **Rate & edit** — click the stars on a record; edit its condition/notes.
- [ ] **Search Discogs to add** — (needs Discogs connected) search and add a
  release; confirm metadata + artwork import.
- [ ] **Barcode scan** — Collection -> + ADD RECORD -> "Scan barcode" -> USE
  CAMERA; scan a record's barcode (needs HTTPS + camera permission) and confirm
  the Discogs match appears. Also try UPLOAD PHOTO with a barcode photo.
- [ ] **Insights -> value** — capture a snapshot; confirm total worth shows and
  (after a second snapshot on another day) the history chart + movers populate.
- [ ] **Insights -> completion** — confirm per-artist owned/missing shows.
- [ ] **Insights -> collector card** — GENERATE CARD; confirm the image renders
  and downloads.
- [ ] **Trip planner** — on a Scout recommendation, plan a road trip; confirm
  gas cost is exact and (with AI on) hotel/flight estimates + booking links show.

## Known follow-ons (not blockers)

Deferred by mutual decision; none block launch:

- Real-time WebSocket chat (the message board polls today).
- "Leave a shared account" endpoint; admin editing a shared account's home hero.
- Custom-image **upload** for the home hero (currently a URL field — needs
  object storage/CDN).
- Automated unit tests for the pure scoring functions (Hunter score, Collector
  DNA).
- Facebook *group* integration is not possible via Meta's API — the group link
  field is the intended behavior.
