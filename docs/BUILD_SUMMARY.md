# SpinningLicorice — What's Been Built

SpinningLicorice is a full-stack app for vinyl-record collectors: collection tracking,
deal-finding, a social layer, and AI assistance. This document summarizes
everything built, from the takeover of an abandoned codebase to a complete,
deployable application.

- **Backend:** FastAPI (Python 3.12), SQLAlchemy 2, Alembic migrations
- **Database:** PostgreSQL 16 + pgvector
- **Frontend:** Next.js 16 (React 19, TypeScript), standalone output
- **Cache / state:** Redis (with in-process fallback)
- **Deploy target:** Railway (Docker), 4 components (Postgres, Redis, API, web)
- **Scale:** 52 API endpoints, 8 migrations

---

## Starting point

The project was inherited as an abandoned codebase ("Dead Wax") after the
original engineer left. A full review found five deploy-blocking issues and
several smaller ones. Every item below was fixed or built from there.

---

## 1. Security & deploy blockers (the original five)

- **Real authentication.** Every route previously used a "first user in the
  table" query, so all visitors shared one account. Replaced with proper JWT
  auth (bcrypt password hashing via pwdlib, tokens via pyjwt) and a
  `get_current_user` dependency. Every route is now scoped to the authenticated
  user.
- **Encrypted third-party tokens.** Discogs OAuth tokens were stored in pl
  aintext columns named `_encrypted`. Now genuinely encrypted at rest (Fernet,
  key derived from `TOKEN_ENCRYPTION_KEY`).
- **Durable OAuth state.** The in-memory `_pending_oauth` dict (which broke
  across restarts/replicas) was replaced with a Redis-backed state store with an
  in-process fallback.
- **Database migrations.** There were none — the app relied on an unauthenticated
  `/dev/bootstrap-db` endpoint. Replaced with a full Alembic migration chain
  (8 migrations) that also creates the required Postgres extensions.
- **Production hardening.** Added Dockerfiles, env-driven CORS, a corrected DB
  driver URL, and a **fail-fast**: the API refuses to boot in production if
  `JWT_SECRET_KEY`, `TOKEN_ENCRYPTION_KEY`, or `DISCOGS_OAUTH_TEMP_SECRET` are
  missing or left at dev defaults.

Also from the review: pinned the frontend's `"latest"` dependencies to real
versions with a committed lockfile, and fixed the Hunter Discogs N+1 (below).

---

## 2. Rename: Dead Wax → SpinningLicorice

A complete, case-correct rename across 43 files, including the `dead_wax_score`
→ `spinninglicorice_score` database column. The column rename was done as an in-place,
data-preserving migration (verified against seeded data), not a drop-and-add.

---

## 3. Account sharing

Grant other people access to **your** account, read-only or as an admin.

- **Login-required invite links** (viewer or admin) with expiry, use limits, and
  revocation. Each member is named and individually revocable.
- **Anonymous public read links** ("anyone with the link") with an **on/off
  privacy toggle** and token regeneration.
- **Permission layer:** an account-context dependency resolves the caller's
  effective role (owner > admin > viewer) via an `X-Account-Id` header;
  read-vs-write is enforced across all routes. Viewers are read-only everywhere.
- Public read views (collection, DNA, home) for the anonymous link, with no
  public write path.

## 4. Social login (Google & Facebook)

- OAuth 2.0 authorization-code flow for Google and Facebook; the backend owns the
  handshake and mints its own JWT, so provider tokens never reach the browser.
- An `OAuthIdentity` model lets one user link both providers; find-or-create
  matches by provider identity, then by email.
- CSRF `state` handled via the shared state store. Unconfigured providers return
  503 cleanly, so you can launch with just one provider.

## 5. Frontend

- Login page (Google/Facebook), OAuth callback capture (token via URL fragment,
  kept out of server logs), a route guard, and token handling with automatic
  bounce-to-login on 401.
- An account switcher for shared accounts (the `X-Account-Id` context).
- Sharing management UI, invite-accept and public shared-view pages.
- Matches the existing warm "vinyl" theme throughout.

## 6. Home personalization

- Feature a **favorite album, an artist, or a custom image/text** as a themed
  hero atop the home dashboard — the cover art becomes a blurred full-bleed
  backdrop so the banner takes on the artwork's color mood.
- Editable **both** inline on the home page and from the Profile page.
- A picker that searches your own collection. Viewers can see but not change a
  shared account's hero.

## 7. Friend groups (social layer)

- **Groups:** create, invite (link-based), join, members, leave — with
  last-admin-leaving auto-promotion so a group never becomes adminless.
- **Message board:** post + poll (a `since` cursor); structured so real-time
  WebSockets can be added later without a data-model change.
- **Swap/sale listings:** list a record for swap or sale, others express
  interest, settlement is **off-app via Venmo/PayPal handles** (the app never
  touches money). Sellers see interested buyers' handles; non-sellers see only
  their own interest.
- Optional Facebook-group **link** field (Meta's API can't create or post to
  Groups, so integration isn't possible — the link is intentional).

## 8. AI features (Anthropic / Claude)

- **Central AI client** — all Claude calls go through one place; everything
  **degrades gracefully** when no API key is set (the app runs fine without it).
- **Natural-language hunt parsing** — Claude (Haiku) turns "early Bowie I don't
  own, VG+ under $40" into structured criteria, with the original regex parser
  kept as an automatic fallback.
- **Web-search-backed enrichment** — Concert Scout briefings and pressing
  research using Anthropic's server-side web search tool, returned with
  citations. User-initiated only and capped (searches cost money).

## 9. Performance & the AI disclosure

- **Hunter Discogs N+1 fixed:** importing a release used to fetch it, then the
  provider fetched the same release again. Now the import's payload is reused —
  release API calls per hunt roughly halved (verified by call-counting).
- **Response caching** (Redis + in-memory fallback): release metadata 24h, price
  suggestions 30min — repeat hunts barely touch the Discogs API.
- **Rate-limit handling:** HTTP 429 responses back off and retry (honoring
  `Retry-After`), so a hunt degrades to "slower," not "failed."
- Per-release failures now log (with id + traceback) instead of failing silently.
- **AI disclosure** in small print at the bottom of **every** page (app, login,
  and public shared views): "This site was created by AI. Information may be
  inaccurate — please do your own research before purchasing anything."

## 10. Launch kit

- `scripts/smoke_test.py` — a one-command post-deploy check of the critical path
  (health, register, login, JWT, protected routes, home feed, hunt create, NL
  parse, group create, AI status, auth enforcement). Verified working against a
  live instance.
- `docs/PRE_LAUNCH_CHECKLIST.md` — ordered steps for credentials, deploy, and the
  by-hand checks that need a browser or real APIs.
- `docs/DEPLOY_RAILWAY.md` — full Railway setup walkthrough.

## 11. Concert road-trip planner

Plan a trip to a scouted show, with a cost estimate:

- **Drive, fly, or compare** — a full multi-day trip plan (depart, drive/fly,
  hotel nights, show, return) as an itinerary.
- **Gas is computed exactly** (distance x price / MPG); **hotel and flight prices
  are AI web-search estimates** with citations, clearly labeled as estimates.
- **Saved defaults, editable per trip** — home location, MPG, gas price, default
  mode/nights live in your preferences; every trip can override them.
- **Expedia booking deep-links** (hotel + flight, prefilled with destination and
  dates). A configurable `EXPEDIA_AFFILIATE_ID` makes them affiliate links that
  earn commission once you're approved; until then they're plain working links.
  Booking links are marked `rel="sponsored"` and the site-wide AI disclosure
  applies — all figures are estimates, nothing is booked or charged in-app.

**Affiliate / referral revenue** (extends the same configurable pattern): the
Scout "Tickets" button becomes an affiliate link (SeatGeek / StubHub / Vivid
Seats / Ticketmaster), and the trip planner adds **rental car** (Expedia /
Rentalcars / Discover Cars) and **rideshare** referral links. Each partner has
its own env var; unset partners produce plain working links (no revenue). All
outbound links are marked `rel="sponsored nofollow"`. Full in-app payments /
a premium subscription tier (Stripe) is deliberately left as a separate future
project rather than a rushed bolt-on.

Degrades gracefully: with AI off, the itinerary, gas, and booking links still
render; only the hotel/flight/distance estimates are omitted.

## 12. Collection insights (value, completion, collector card)

Three collector-facing features that turn stored data into things worth coming
back for:

- **Collection value tracking** — an estimated total worth, a worth-over-time
  history chart from periodic snapshots, and best/worst *movers* (which records
  gained or lost the most since the last snapshot). Values come from cached
  Discogs price data, falling back to what you paid; the UI shows how much of the
  collection is market-valued so the number is honest.
- **Complete the collection** — for each artist you collect, how many of their
  known releases you own vs. are missing (e.g. "Miles Davis 2/3 · 67%"), with the
  missing titles listed. Turns the collection into a hunt list.
- **Shareable Collector Card** — a good-looking 1200×630 image (records, worth,
  era, top labels, and a deterministic rarity score/tier) rendered server-side as
  SVG, ready to post. No image library needed; downloads directly.

Served by four endpoints under `/insights` (value, snapshot, completion, card);
reads require account read, capturing a snapshot requires write.

## 13. Adding & rating records (manual + Discogs search)

Records no longer come only from a bulk Discogs sync. There are now three ways
in, plus full editing:

- **Add by hand** — type in title, artist, year, label, condition, price, a
  1–5 star rating, and notes. Creates a lightweight release under
  `source="manual"`.
- **Search Discogs and pick** — search Discogs by text and add the exact release
  (reuses the existing importer so metadata/artwork come in clean). Requires a
  connected Discogs account; fails with a clear "connect first" message if not.
- **Rate & edit any record** — a 1–5 star rating (click to set) plus editable
  condition, notes, and purchase price on every card, whatever its source. The
  `personal_rating`/`personal_notes` fields — previously stored but never
  exposed — are now surfaced in the collection list and editable inline.
- **Remove a record.**

Endpoints (all writes require account write; viewers are read-only):
`POST /collection` (manual), `GET /collection/search`, `POST /collection/from-discogs`,
`PATCH /collection/{id}` (edit/rate), `DELETE /collection/{id}`.

## 14. Barcode scanning (camera + photo)

Point your phone at a record's barcode to find and add it:

- **Live camera scan** — decodes the barcode in-browser (ZXing), then looks it
  up on Discogs and shows matches to pick and add.
- **Photo upload** — same, from a photo of the barcode (works when the live
  camera isn't available; the file input uses the rear camera on phones).
- The decoded barcode is cleaned (hyphens/spaces stripped) and validated, then
  looked up via `GET /collection/scan?barcode=…` (Discogs barcode search), which
  requires a connected Discogs account and degrades with a clear message if not.

Only *barcode* scanning is included — reliable and mature. Photo-of-cover
recognition (matching artwork to a release) was deliberately left out: it needs
image-recognition infrastructure and is error-prone, so it's a separate future
project. QR scanning would use the same camera tech but records carry no
standard identifying QR code, so it isn't wired up.

**Verification caveat:** the barcode→Discogs lookup, cleaning, validation, error
handling, and UI all build and are tested here, but the actual camera decode
only runs in a real browser (HTTPS/localhost + camera permission), so it's a
first-deploy verification item.

---

## Migrations (in order)

| # | Migration | What it adds |
|---|-----------|--------------|
| 0001 | extensions | pgvector + pgcrypto |
| 0002 | initial schema | core tables |
| 0003 | user auth fields | password hash, is_active |
| 0004 | rename score column | `dead_wax_score` → `spinninglicorice_score` (in place) |
| 0005 | account sharing | memberships, invites, public shares |
| 0006 | oauth identities | Google/Facebook links |
| 0007 | home feature | home personalization |
| 0008 | social layer | groups, messages, listings, payment handles |
| 0009 | value tracking | release valuations + collection value snapshots |

---

## What's verified vs. what needs a live deploy

**Verified in development** (against a live Postgres + real frontend builds):
every migration from an empty DB, the full auth/sharing/groups permission
matrices, hunt parsing (AI path via mocks + regex fallback), the N+1 fix by
call-counting, caching and 429 retry, graceful AI degradation, and the smoke
test itself running green against a live API.

**Needs the real deploy** (couldn't be done here — no Docker, no real
credentials, no browser): the first Docker image build, the live
Google/Facebook/Discogs round-trips, real Anthropic calls, and a browser
click-through of the UI. See `PRE_LAUNCH_CHECKLIST.md`.

## Known follow-ons (not blockers)

Real-time WebSocket chat; "leave a shared account" endpoint; admin editing a
shared account's hero; custom-image **upload** for the hero (needs object
storage); automated unit tests for the pure scoring functions.
