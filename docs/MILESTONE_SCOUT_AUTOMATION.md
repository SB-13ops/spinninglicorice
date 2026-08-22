# Milestone — Real Scout + Auto Hunt Alerts

## Real Concert Scout

SpinningLicorice now includes a Ticketmaster Discovery API provider.

Scout uses:
- Collector DNA artist affinities
- user location/radius
- Ticketmaster music-event discovery
- event/attraction matching
- venue and date information
- Scout Score
- explanation text

### Configuration

Set:

```env
TICKETMASTER_API_KEY=...
```

Add the user's ZIP/postal code to `user_preferences.location_text` and radius to `radius_miles`.

Then run:

```bash
POST /api/v1/scout/refresh
GET  /api/v1/scout/recommendations
```

## Scout Score V1

- Artist match: 40%
- Related-artist match: 20%
- Genre match: 15%
- Distance: 15%
- Event confidence: 10%

## Auto Hunt / Scout notifications

V1 now has a domain-level automation runner and notification endpoints:

```bash
POST /api/v1/notifications/refresh
GET  /api/v1/notifications
```

It creates:
- Hunter alerts for active Auto Hunts with scores >= 85
- Scout alerts for event recommendations with scores >= 88

Notifications are deduplicated so repeated refreshes do not create the same alert again.

## Home feed

Home now promotes:
- top Hunter opportunity as **SpinningLicorice Pick**
- next-best Hunter results
- top Concert Scout recommendation
- recent Hunter/Scout alerts

This closes a major V1 loop:

```text
Collection
  ↓
Collector DNA
  ↓
Hunter + Scout
  ↓
Alerts
  ↓
Home
```

## Production background jobs

The V1 runner is synchronous by design. For hosted beta, invoke these same domain services from a scheduler/queue:

- refresh Auto Hunts
- refresh Scout
- generate notifications
- refresh Home feed state

No domain redesign is required when moving to a real worker system.
