# Burnt Jacket V1 Architecture

## Product loop

Collection → Music DNA + Collector DNA → Recommendations → Hunter → New Records → Scout → New Artists → Collection

## Modular-monolith modules

### Accounts
User identity, profile, location, radius, notification preferences.

### Catalog
Artists, albums, releases, labels, genres, external identifiers.

### Collection
Owned records and personal-copy metadata.

### Integrations
Discogs OAuth, import, synchronization and supported write-back.

### Collector DNA
Structured preferences inferred from collection and behavior.

### Hunter
Saved hunts, normalized marketplace listings, opportunity scoring and alerts.

### Recommendations
Personalized record recommendations and explanation payloads.

### Scout
Events, event-artist matching, distance and recommendation scoring.

### Feedback
Own, want, like, dislike, interested, saw them and similar signals.

### Notifications
Hunt matches, value drops, wantlist deals and concert alerts.

## Important model decisions

1. **Album != Release.**
   An album is the musical work/edition family. A release is a specific pressing/version.

2. **Burnt Jacket owns its identifiers.**
   External sources such as Discogs map onto Burnt Jacket records rather than becoming the primary database keys.

3. **Discogs is optional.**
   Users can maintain a Burnt Jacket-native collection.

4. **AI does not own deterministic logic.**
   Ownership, price comparisons, conditions and hard Hunt criteria remain structured application logic.

5. **The LLM layer is used for language and reasoning.**
   Natural-language Hunt parsing, explanations and recommendation narratives are examples.

## Request flow

```text
Next.js
  ↓
FastAPI
  ↓
Domain services
  ↓
PostgreSQL / pgvector
  ↓
External adapters
```
