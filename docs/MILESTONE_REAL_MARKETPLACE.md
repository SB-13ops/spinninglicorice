# Milestone — Real Marketplace + Pressing Matching

## What changed

Hunter now prefers **real Discogs marketplace data** whenever the user has connected a Discogs account.

The real flow is:

```text
Natural-language Hunt
    ↓
Discogs database search
    ↓
Exact Discogs Release ID
    ↓
Burnt Jacket release mapping
    ↓
Discogs marketplace summary
    ↓
Discogs price suggestions
    ↓
Exact ownership / Wantlist check
    ↓
Burnt Jacket Score
    ↓
Hunter result
```

## Pressing matching

For Discogs-sourced opportunities, the match is exact:

`Discogs release ID → external_mappings → Burnt Jacket release ID`

This receives a **100% release-match confidence** because it represents the same Discogs release imported into the Burnt Jacket catalog.

A metadata fallback matcher is also included for future providers that do not expose Discogs IDs. It scores:

- title
- artist
- year
- catalog number
- country

The fuzzy fallback only returns a match above the configured confidence threshold.

## Real marketplace data

Burnt Jacket now uses the connected Discogs API for:

- release discovery
- current `lowest_price`
- `num_for_sale`
- marketplace price suggestions by condition
- exact release metadata
- marketplace navigation

Important distinction: this V1 integration shows a **real release-level marketplace opportunity**. It does not pretend the lowest-price figure is an individual seller listing when the API response only provides release-level market data.

## Ownership intelligence

Because Hunter resolves the exact Burnt Jacket release, it can now answer:

- **OWNED** — the exact release is already in the user's Collection
- **WANTLIST** — the exact release is already on the user's Wantlist
- **NOT OWNED** — the exact release is absent from the Collection

Hunts containing phrases such as `I don't own` exclude exact releases already owned.

## Fallback behavior

If Discogs is not connected, Hunter uses the local demo provider.

If Discogs is connected but returns no matching opportunities, the current development build also falls back to demo data so the rest of the UI remains testable.

For hosted beta, that fallback should be replaced by a clear "no current matches" state.

## Next build

The strongest next milestone is:

1. **Scout real concert provider**
2. Home feed promotion of top Hunter opportunity
3. Auto Hunt background jobs + alerts
4. Real authentication and encrypted external tokens
