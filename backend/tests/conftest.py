"""Shared fixtures for backend tests."""
import os
import tempfile
import pytest
from fastapi.testclient import TestClient

# Use a temp DB for every test session
@pytest.fixture(scope="session")
def tmp_db(tmp_path_factory):
    db_path = str(tmp_path_factory.mktemp("data") / "test.db")
    os.environ["DB_FILE"] = db_path
    return db_path


@pytest.fixture(scope="session")
def client(tmp_db):
    # Import app AFTER setting DB_FILE so init_db uses the temp path
    from backend.main import app
    from backend.database import init_db
    init_db()
    return TestClient(app)


@pytest.fixture
def auth_headers(client):
    """Register a fresh test user and return Authorization headers."""
    import uuid
    username = f"testuser_{uuid.uuid4().hex[:6]}"
    resp = client.post("/api/auth/register", json={"username": username, "password": "testpass123"})
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seeded_board(client, auth_headers):
    """Returns (board_id, col_id) from the auto-created board for a new user."""
    resp = client.get("/api/boards", headers=auth_headers)
    assert resp.status_code == 200
    boards = resp.json()
    assert len(boards) > 0
    board_id = boards[0]["id"]

    resp2 = client.get(f"/api/boards/{board_id}", headers=auth_headers)
    col_id = resp2.json()["columns"][0]["id"]
    return board_id, col_id
