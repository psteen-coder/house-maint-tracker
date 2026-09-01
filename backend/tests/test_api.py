import os
import tempfile

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    monkeypatch.setenv("HOUSE_MAINT_DB", f"sqlite:///{dbfile}")
    # Import after env is set so engine points at the temp db.
    import importlib
    import app.main as main

    importlib.reload(main)
    main.Base.metadata.create_all(main.engine)
    db = main.SessionLocal()
    try:
        from app.seed import seed_if_empty

        seed_if_empty(db)
    finally:
        db.close()
    with TestClient(main.app) as c:
        yield c


def _login(client, email, password):
    r = client.post("/api/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["ok"] is True


def test_admin_creates_user_member_cannot_delete(client):
    admin = _login(client, "patrick@1944dinius.local", "adminpass")
    r = client.post(
        "/api/users",
        headers=admin,
        json={"name": "Sam", "email": "sam@1944dinius.local", "password": "x", "role": "member"},
    )
    assert r.status_code == 200
    new_id = r.json()["id"]
    member = _login(client, "alex@1944dinius.local", "memberpass")
    denied = client.delete(f"/api/users/{new_id}", headers=member)
    assert denied.status_code == 403
    ok = client.delete(f"/api/users/{new_id}", headers=admin)
    assert ok.status_code == 200


def test_viewer_cannot_mutate(client):
    viewer = _login(client, "jamie@1944dinius.local", "viewerpass")
    r = client.post("/api/tasks", headers=viewer, json={"title": "Nope"})
    assert r.status_code == 403
    board = client.get("/api/kanban", headers=viewer)
    assert board.status_code == 200


def test_kanban_windows(client):
    admin = _login(client, "patrick@1944dinius.local", "adminpass")
    board = client.get("/api/kanban", headers=admin).json()
    assert set(board) == {"due", "in_progress", "completed"}
    assert len(board["completed"]) >= 1
    # completed column only last week — seeded done is today
    for card in board["completed"]:
        assert card["status"] == "done"


def test_start_and_complete_occurrence(client):
    admin = _login(client, "patrick@1944dinius.local", "adminpass")
    occs = client.get("/api/occurrences", headers=admin).json()
    open_card = next(o for o in occs if o["status"] == "todo" and not o["blocked"])
    r = client.patch(
        f"/api/occurrences/{open_card['id']}",
        headers=admin,
        json={"status": "in_progress"},
    )
    assert r.status_code == 200
    assert r.json()["status"] == "in_progress"
    board = client.get("/api/kanban", headers=admin).json()
    assert any(c["id"] == open_card["id"] for c in board["in_progress"])


def test_assignee_stored(client):
    admin = _login(client, "patrick@1944dinius.local", "adminpass")
    users = {u["name"]: u for u in client.get("/api/users", headers=admin).json()}
    occs = client.get("/api/occurrences", headers=admin).json()
    card = occs[0]
    r = client.patch(
        f"/api/occurrences/{card['id']}",
        headers=admin,
        json={"assignee_id": users["Alex"]["id"]},
    )
    assert r.status_code == 200
    assert r.json()["assignee_id"] == users["Alex"]["id"]
    assert r.json()["assignee_name"] == "Alex"


def test_calendar_has_month_days(client):
    admin = _login(client, "patrick@1944dinius.local", "adminpass")
    cal = client.get("/api/calendar", headers=admin).json()
    assert "days" in cal
    assert cal["year"] and cal["month"]
