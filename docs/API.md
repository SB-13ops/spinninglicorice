# SpinningLicorice V1 API Surface

Base path: `/api/v1`

## Health
- `GET /health`

## Collection
- `GET /collection`
- `POST /collection`
- `GET /collection/{collection_item_id}`
- `PATCH /collection/{collection_item_id}`
- `DELETE /collection/{collection_item_id}`

## Catalog
- `GET /catalog/search?q=`
- `GET /releases/{release_id}`
- `GET /artists/{artist_id}`

## Discogs
- `GET /integrations/discogs/connect`
- `GET /integrations/discogs/callback`
- `POST /integrations/discogs/sync`
- `GET /integrations/discogs/status`

## Collector DNA
- `GET /dna`
- `POST /dna/rebuild`

## Hunter
- `GET /hunts`
- `POST /hunts`
- `GET /hunts/{hunt_id}`
- `PATCH /hunts/{hunt_id}`
- `DELETE /hunts/{hunt_id}`
- `GET /hunts/{hunt_id}/results`
- `POST /hunter/parse`

## Recommendations
- `GET /recommendations`
- `POST /recommendations/{recommendation_id}/feedback`

## Scout
- `GET /scout/events`
- `GET /scout/recommendations`
- `POST /scout/{recommendation_id}/feedback`

## Home
- `GET /home/feed`

The Home endpoint should aggregate already-computed domain data instead of embedding business logic directly in the route.
