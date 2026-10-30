import uuid

from app.models.core import Album, CollectionItem, Notification, Release

from .conftest import register, share_account, user_id


def _add_record(db, owner_id):
    album = Album(title="Blue")
    db.add(album)
    db.flush()
    release = Release(album_id=album.id, title="Blue")
    db.add(release)
    db.flush()
    db.add(CollectionItem(
        user_id=owner_id, release_id=release.id, purchase_price=42, personal_notes="private note"
    ))
    db.add(Notification(user_id=owner_id, notification_type="hunter", title="secret", body="secret"))
    db.commit()


def test_public_link_hides_private_fields(client, db):
    owner = register(client, "owner@example.com")
    _add_record(db, uuid.UUID(user_id(client, owner)))
    token = client.put("/api/v1/sharing/public", json={"enabled": True}, headers=owner).json()["token"]

    item = client.get(f"/api/v1/public/{token}/collection").json()["items"][0]
    assert item["title"] == "Blue"
    assert "purchase_price" not in item and "personal_notes" not in item
    assert client.get(f"/api/v1/public/{token}/home").json()["notifications"] == []

    # The owner still sees everything.
    own = client.get("/api/v1/collection", headers=owner).json()["items"][0]
    assert own["purchase_price"] == 42 and own["personal_notes"] == "private note"


def test_viewer_is_read_only(client):
    owner = register(client, "owner@example.com")
    viewer = share_account(client, owner, register(client, "viewer@example.com"), "viewer")

    assert client.get("/api/v1/collection", headers=viewer).status_code == 200
    assert client.get("/api/v1/trips/defaults", headers=viewer).status_code == 200
    assert client.put("/api/v1/trips/defaults", json={"home_location": "Nowhere"}, headers=viewer).status_code == 403
    assert client.get("/api/v1/collection/search", params={"q": "x"}, headers=viewer).status_code == 403
    assert client.post("/api/v1/ai/pressing/research", json={"title": "x"}, headers=viewer).status_code == 403


def test_board_works_and_admins_cannot_post_as_owner(client):
    owner = register(client, "owner@example.com")
    admin = share_account(client, owner, register(client, "admin@example.com"), "admin")

    assert client.get("/api/v1/board", headers=owner).status_code == 200
    resp = client.post(f"/api/v1/board/{uuid.uuid4()}/comments", json={"message": "hi"}, headers=admin)
    assert resp.status_code == 403


def test_malformed_ids_are_client_errors(client):
    owner = register(client, "owner@example.com")
    assert client.patch("/api/v1/sharing/members/not-a-uuid", json={"role": "viewer"}, headers=owner).status_code == 422
    assert client.delete("/api/v1/sharing/invites/not-a-uuid", headers=owner).status_code == 422
