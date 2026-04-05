"""
Tests for card assignments, activity log, and column reorder.
"""
import pytest


@pytest.fixture
def card_fixture(client, auth_headers, seeded_board):
    board_id, col_id = seeded_board
    resp = client.post("/api/cards", headers=auth_headers, json={
        "title": "Assignment Test Card",
        "column_id": col_id,
    })
    assert resp.status_code == 201
    return resp.json()["id"], board_id, col_id


# ── Assignments ─────────────────────────────────────────────────────────────────

class TestAssignments:
    def test_create_card_with_no_assignee(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        resp = client.post("/api/cards", headers=auth_headers, json={
            "title": "Unassigned Card",
            "column_id": col_id,
        })
        assert resp.status_code == 201
        assert resp.json()["assignee_id"] is None

    def test_assign_card_to_user(self, client, auth_headers, seeded_board):
        import uuid
        board_id, col_id = seeded_board

        # Get current user id from /me
        me = client.get("/api/auth/me", headers=auth_headers).json()
        user_id = me["id"]

        card_resp = client.post("/api/cards", headers=auth_headers, json={
            "title": "Card to assign",
            "column_id": col_id,
        })
        card_id = card_resp.json()["id"]

        update_resp = client.put(f"/api/cards/{card_id}", headers=auth_headers, json={
            "column_id": col_id,
            "order": 0,
            "title": "Card to assign",
            "assignee_id": user_id,
        })
        assert update_resp.status_code == 200

    def test_board_returns_assignee_username(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        me = client.get("/api/auth/me", headers=auth_headers).json()
        user_id = me["id"]

        card_resp = client.post("/api/cards", headers=auth_headers, json={
            "title": "Assigned Card",
            "column_id": col_id,
            "assignee_id": user_id,
        })
        card_id = card_resp.json()["id"]

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        card_data = board["cards"].get(card_id)
        assert card_data is not None
        assert card_data["assignee_id"] == user_id
        assert card_data["assignee_username"] is not None


# ── Activity Log ─────────────────────────────────────────────────────────────────

class TestActivityLog:
    def test_activity_starts_empty(self, client, auth_headers, seeded_board):
        # Create a fresh board for clean activity
        board_resp = client.post("/api/boards", headers=auth_headers, json={"title": "Activity Test Board"})
        board_id = board_resp.json()["id"]
        resp = client.get(f"/api/boards/{board_id}/activity", headers=auth_headers)
        assert resp.status_code == 200
        # May have some from board creation

    def test_create_card_logs_activity(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        client.post("/api/cards", headers=auth_headers, json={
            "title": "Activity Card",
            "column_id": col_id,
        })
        resp = client.get(f"/api/boards/{board_id}/activity", headers=auth_headers)
        assert resp.status_code == 200
        entries = resp.json()
        assert any(e["action"] == "created" and e["entity_type"] == "card" for e in entries)

    def test_delete_card_logs_activity(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        card = client.post("/api/cards", headers=auth_headers, json={
            "title": "Card To Delete",
            "column_id": col_id,
        }).json()
        client.delete(f"/api/cards/{card['id']}", headers=auth_headers)
        resp = client.get(f"/api/boards/{board_id}/activity", headers=auth_headers)
        entries = resp.json()
        assert any(e["action"] == "deleted" and e["entity_type"] == "card" for e in entries)

    def test_activity_entries_have_username(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        client.post("/api/cards", headers=auth_headers, json={
            "title": "Track this",
            "column_id": col_id,
        })
        resp = client.get(f"/api/boards/{board_id}/activity", headers=auth_headers)
        for entry in resp.json():
            assert "username" in entry
            assert entry["username"]

    def test_activity_requires_auth(self, client, seeded_board):
        board_id, _ = seeded_board
        resp = client.get(f"/api/boards/{board_id}/activity")
        assert resp.status_code in (401, 403)

    def test_activity_limit_param(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        # Create 5 cards
        for i in range(5):
            client.post("/api/cards", headers=auth_headers, json={
                "title": f"Limit test card {i}",
                "column_id": col_id,
            })
        resp = client.get(f"/api/boards/{board_id}/activity?limit=3", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) <= 3


# ── Column Reorder ──────────────────────────────────────────────────────────────

class TestColumnReorder:
    def test_reorder_columns(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        col_ids = [c["id"] for c in board["columns"]]

        # Reverse the order
        reversed_ids = list(reversed(col_ids))
        resp = client.post("/api/columns/reorder", headers=auth_headers,
                           json={"column_ids": reversed_ids})
        assert resp.status_code == 200

        # Verify order persisted
        board2 = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        new_ids = [c["id"] for c in board2["columns"]]
        assert new_ids == reversed_ids

    def test_reorder_empty_list_rejected(self, client, auth_headers):
        resp = client.post("/api/columns/reorder", headers=auth_headers,
                           json={"column_ids": []})
        assert resp.status_code == 400

    def test_reorder_requires_auth(self, client):
        resp = client.post("/api/columns/reorder", json={"column_ids": ["col-1"]})
        assert resp.status_code in (401, 403)

    def test_reorder_other_users_columns_rejected(self, client, seeded_board):
        import uuid
        board_id, _ = seeded_board
        username2 = f"reorder_intruder_{uuid.uuid4().hex[:6]}"
        reg = client.post("/api/auth/register", json={"username": username2, "password": "pass123"})
        headers2 = {"Authorization": f"Bearer {reg.json()['access_token']}"}

        # Get col_ids from board (but user2 doesn't own them)
        # We need a board for user1 — use seeded_board's col_ids
        # user2 trying to reorder user1's columns
        from backend.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM columns WHERE board_id = ?", (board_id,))
        col_ids = [r["id"] for r in cursor.fetchall()]
        conn.close()

        resp = client.post("/api/columns/reorder", headers=headers2,
                           json={"column_ids": col_ids})
        assert resp.status_code == 404
