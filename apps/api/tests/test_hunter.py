import uuid

from app.api.routes import hunter as hunter_routes
from app.models.core import Album, ExternalAccount, Release
from app.services.discogs_hunter_provider import DiscogsOpportunity

from .conftest import register, user_id


def _release(db) -> uuid.UUID:
    album = Album(title="Workingman's Dead")
    db.add(album)
    db.flush()
    release = Release(album_id=album.id, title="Workingman's Dead")
    db.add(release)
    db.commit()
    return release.id


class _FakeProvider:
    release_id: uuid.UUID
    seen_user_id = None

    def __init__(self, db, *, user):
        _FakeProvider.seen_user_id = user.id

    def search(self, criteria, *, limit=12):
        return [
            DiscogsOpportunity(
                discogs_release_id="123",
                spinninglicorice_release_id=self.release_id,
                title="Workingman's Dead",
                artist="Grateful Dead",
                year=1970,
                country="US",
                image_url=None,
                current_lowest_price=20.0,
                num_for_sale=4,
                estimated_low=25.0,
                estimated_high=40.0,
                media_condition_basis="VG+",
                owned=False,
                on_wantlist=True,
                marketplace_url="https://www.discogs.com/sell/release/123",
            )
        ]


def test_refresh_uses_discogs_for_connected_accounts(client, db, monkeypatch):
    headers = register(client, "hunter@example.com")
    owner_id = uuid.UUID(user_id(client, headers))
    db.add(ExternalAccount(user_id=owner_id, provider="discogs", username="hunter"))
    db.commit()
    _FakeProvider.release_id = _release(db)
    monkeypatch.setattr(hunter_routes, "DiscogsHunterProvider", _FakeProvider)

    hunt_ids = [
        client.post("/api/v1/hunter/hunts", json={"name": n, "query": "grateful dead"}, headers=headers).json()["id"]
        for n in ("first", "second")
    ]
    for hunt_id in hunt_ids:
        # Both hunts surface the same Discogs release; neither may collide.
        resp = client.post(f"/api/v1/hunter/hunts/{hunt_id}/refresh", headers=headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["provider"] == "discogs"
    assert _FakeProvider.seen_user_id == owner_id

    # Refreshing again replaces this hunt's results rather than duplicating them.
    resp = client.post(f"/api/v1/hunter/hunts/{hunt_ids[0]}/refresh", headers=headers)
    assert resp.status_code == 200, resp.text
    results = client.get(f"/api/v1/hunter/hunts/{hunt_ids[0]}/results", headers=headers).json()["items"]
    assert len(results) == 1


def test_parse_requires_login(client):
    assert client.post("/api/v1/hunter/parse", json={"query": "dead under $30"}).status_code == 401
