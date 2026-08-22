# Railway Environment Variables

Every variable SpinningLicorice reads, which service it belongs to, and whether it's
required. Variable names are taken directly from the code.

Two app services need variables: **API** (`apps/api`) and **web** (`apps/web`).
The Postgres and Redis plugins provide their own connection variables, which you
reference from the API service.

Legend: **Required** = the app won't work (or won't boot) without it.
**Optional** = a feature stays off until you set it; the app runs fine.

---

## Quick start — the minimum to boot

Set these on the **API** service and the app will start and serve auth +
collection + groups (no third-party integrations yet):

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

And on the **web** service:

```
NEXT_PUBLIC_API_BASE_URL=https://<your-api-domain>/api/v1
```

> The API **refuses to boot in production** if `JWT_SECRET_KEY`,
> `TOKEN_ENCRYPTION_KEY`, or `DISCOGS_OAUTH_TEMP_SECRET` are missing or left at
> their dev defaults. This is intentional.

### Generate the three secrets

```bash
# JWT_SECRET_KEY  (must be at least 32 bytes)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# TOKEN_ENCRYPTION_KEY  (a Fernet key)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# DISCOGS_OAUTH_TEMP_SECRET  (any strong random string)
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## API service — full variable list

### Core (required)

| Variable | Required | Example / value | Notes |
|----------|----------|-----------------|-------|
| `APP_ENV` | **Yes** | `production` | Enables the production security fail-fast. |
| `DATABASE_URL` | **Yes** | `${{Postgres.DATABASE_URL}}` | From the Postgres plugin. Plain `postgres://` is auto-normalized to the psycopg driver. |
| `REDIS_URL` | **Yes** | `${{Redis.REDIS_URL}}` | From the Redis plugin. Used for OAuth state + Discogs cache. |
| `JWT_SECRET_KEY` | **Yes** | *(generated, ≥32 bytes)* | Signs auth tokens. |
| `TOKEN_ENCRYPTION_KEY` | **Yes** | *(generated Fernet key)* | Encrypts stored Discogs tokens. |
| `DISCOGS_OAUTH_TEMP_SECRET` | **Yes** | *(generated)* | Protects the Discogs OAuth handshake. |
| `API_BASE_URL` | **Yes** | `https://<api-domain>` | Used to build OAuth redirect URIs. |
| `WEB_BASE_URL` | **Yes** | `https://<web-domain>` | Post-login landing + share/invite links. |
| `CORS_ALLOW_ORIGINS` | **Yes** | `https://<web-domain>` | Comma-separate multiple origins. Must match the web domain. |

### Discogs (needed for collection sync + Hunter)

| Variable | Required | Notes |
|----------|----------|-------|
| `DISCOGS_CONSUMER_KEY` | For Discogs | From your Discogs developer app. |
| `DISCOGS_CONSUMER_SECRET` | For Discogs | " |
| `DISCOGS_CALLBACK_URL` | For Discogs | `https://<api-domain>/api/v1/integrations/discogs/callback` |
| `DISCOGS_USER_AGENT` | Optional | Defaults to `SpinningLicorice/0.1`. |

### Social login (Google / Facebook)

| Variable | Required | Notes |
|----------|----------|-------|
| `GOOGLE_CLIENT_ID` | For Google login | Redirect URI: `https://<api-domain>/api/v1/auth/google/callback` |
| `GOOGLE_CLIENT_SECRET` | For Google login | " |
| `FACEBOOK_CLIENT_ID` | For Facebook login | Redirect URI: `https://<api-domain>/api/v1/auth/facebook/callback` |
| `FACEBOOK_CLIENT_SECRET` | For Facebook login | " |

> Each provider is independent — set only Google, only Facebook, or both. An
> unconfigured provider returns 503 and its button won't work; the other still does.

### AI (Anthropic / Claude) — optional

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `ANTHROPIC_API_KEY` | Optional | *(unset)* | Enables NL hunt parsing + web-search enrichment. Without it, AI features stay off and hunt parsing uses the regex fallback. |
| `AI_FAST_MODEL` | Optional | `claude-haiku-4-5` | Model for parsing / short completions. |
| `AI_RESEARCH_MODEL` | Optional | `claude-sonnet-5` | Model for web-search research. |
| `AI_WEB_SEARCH_MAX_USES` | Optional | `3` | Cap on searches per enrichment (each search is billed). |

> Model names change over time — check Anthropic's current model list and adjust
> `AI_FAST_MODEL` / `AI_RESEARCH_MODEL` if needed.

### Other (optional)

| Variable | Required | Notes |
|----------|----------|-------|
| `TICKETMASTER_API_KEY` | Optional | Concert Scout event data, if used. |

---

## Web service — full variable list

| Variable | Required | Value | Notes |
|----------|----------|-------|-------|
| `NEXT_PUBLIC_API_BASE_URL` | **Yes** | `https://<api-domain>/api/v1` | ⚠️ Inlined at **build time**. Change it → **redeploy** the web service (a restart won't do). |

---

## Referencing the plugin variables

Railway exposes plugin connection strings you reference with `${{...}}`:

- `DATABASE_URL=${{Postgres.DATABASE_URL}}`
- `REDIS_URL=${{Redis.REDIS_URL}}`

(The plugin names must match what you named them; `Postgres` and `Redis` are the
defaults.)

---

## Ready-to-fill template

Copy, fill in, and paste into Railway (API service):

```
APP_ENV=production
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
JWT_SECRET_KEY=
TOKEN_ENCRYPTION_KEY=
DISCOGS_OAUTH_TEMP_SECRET=
API_BASE_URL=https://
WEB_BASE_URL=https://
CORS_ALLOW_ORIGINS=https://
DISCOGS_CONSUMER_KEY=
DISCOGS_CONSUMER_SECRET=
DISCOGS_CALLBACK_URL=https://<api-domain>/api/v1/integrations/discogs/callback
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
FACEBOOK_CLIENT_ID=
FACEBOOK_CLIENT_SECRET=
ANTHROPIC_API_KEY=
AI_FAST_MODEL=claude-haiku-4-5
AI_RESEARCH_MODEL=claude-sonnet-5
AI_WEB_SEARCH_MAX_USES=3
```

Web service:

```
NEXT_PUBLIC_API_BASE_URL=https://<api-domain>/api/v1
```

### Trip planner (Concert road trips) — optional

| Variable | Required | Default | Notes |
|----------|----------|---------|-------|
| `EXPEDIA_AFFILIATE_ID` | Optional | *(unset)* | Your Expedia affiliate/creator tracking ID (apply at creator.expediagroup.com/affiliates). When set, hotel/flight booking links carry your tag and eligible bookings earn commission. When empty, links are plain (working) Expedia searches. |
| `DEFAULT_GAS_PRICE_USD` | Optional | `3.50` | Fallback $/gallon when the user hasn't set their own. |

### Affiliate / referral revenue (Concert + trip) — optional

All optional and independent. Set the ones you're approved for; unset partners
just produce plain (working) links with no revenue.

| Variable | Notes |
|----------|-------|
| `TICKET_AFFILIATE_PROVIDER` | `seatgeek`, `stubhub`, `vividseats`, or `ticketmaster`. |
| `TICKET_AFFILIATE_ID` | Your tracking ID for that ticket program. |
| `CAR_AFFILIATE_PROVIDER` | `expedia` (default), `rentalcars`, or `discovercars`. |
| `CAR_AFFILIATE_ID` | Tracking ID for a dedicated car program (Expedia reuses `EXPEDIA_AFFILIATE_ID`). |
| `RIDESHARE_PROVIDER` | `uber` or `lyft` (label only). |
| `RIDESHARE_REFERRAL_URL` | Your rideshare referral link; the button only shows when set. |
