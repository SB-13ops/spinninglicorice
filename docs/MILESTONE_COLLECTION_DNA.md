# Milestone — Live Collection + Collector DNA V1

## What now works

### Collection
`GET /api/v1/collection` returns imported SpinningLicorice collection rows with:
- release
- artists
- year
- country
- label
- catalog number
- pressing text
- album image
- personal-copy conditions
- purchase price
- source

The Next.js Collection page reads this endpoint and renders the actual records in the approved SpinningLicorice visual style.

### Collector DNA V1
`POST /api/v1/dna/rebuild` analyzes the imported collection using deterministic logic.

Current signals:
- record count
- strongest artists by collection frequency
- strongest labels
- country tendencies
- collection year span
- typical purchase-price interquartile range, where available
- most common media condition, where available

`GET /api/v1/dna` returns the saved profile.

### Home
The Home feed now reads real:
- collection count
- wantlist count
- top artist signal
- Collector DNA state

## First real local workflow

1. Start PostgreSQL.
2. Start FastAPI.
3. `alembic upgrade head` (from apps/api/, creates the schema via migrations)
4. Connect Discogs.
5. `POST /api/v1/integrations/discogs/sync`
6. `POST /api/v1/dna/rebuild`
7. Start Next.js.
8. Open `/collection`, `/dna`, and `/`.

## Next milestone

Hunter should be the next major build:
- saved Hunt CRUD
- natural-language Hunt parser
- provider-neutral listing model
- collection ownership checks
- SpinningLicorice Score V1
- “why this is a match” explanation payload
