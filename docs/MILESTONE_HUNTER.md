# Milestone — Hunter V1

Hunter now works end-to-end with:

- natural-language Hunt parsing
- saved Hunts
- Auto Hunt metadata
- Hunt editing and deletion
- provider-neutral marketplace listings
- a demo marketplace adapter for local testing
- Burnt Jacket Score V1
- explainable deal labels
- interactive Hunter web UI

## Burnt Jacket Score V1

Weights:

- Collector DNA match: 25%
- Price vs estimated market: 25%
- Collection gap / Wantlist: 20%
- Pressing match: 10%
- Condition: 10%
- Listing confidence: 10%

Labels:

- 90–100: GREAT BUY
- 80–89: GOOD BUY
- 65–79: FAIR
- 50–64: WATCH
- below 50: SKIP

## Local test flow

1. Start PostgreSQL and FastAPI.
2. Bootstrap the database.
3. Start the Next.js app.
4. Open `/hunter`.
5. Create a Hunt such as:
   `Grateful Dead records I don't own under $50 VG+`
6. Preview criteria.
7. Create the Hunt.
8. Run Hunt.
9. View scored demo opportunities.

## Next milestone

Replace the demo provider with the first real marketplace/listing source and add release matching so Hunter can answer:

- Do I already own this exact release?
- Is it on my Wantlist?
- Is this the pressing I actually care about?
- What has this specific pressing been selling for?
