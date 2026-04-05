"""
Integration tests for comments, checklist, sharing, and export endpoints.
"""
import pytest


@pytest.fixture
def card_id(client, auth_headers, seeded_board):
    board_id, col_id = seeded_board
    resp = client.post("/api/cards", headers=auth_headers, json={
        "title": "Test Card",
        "details": "Details here",
        "column_id": col_id,
    })
    assert resp.status_code == 201
    return resp.json()["id"]


# ── Comments ────────────────────────────────────────────────────────────────────

class TestComments:
    def test_list_comments_empty(self, client, auth_headers, card_id):
        resp = client.get(f"/api/cards/{card_id}/comments", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_comment(self, client, auth_headers, card_id):
        resp = client.post(f"/api/cards/{card_id}/comments", headers=auth_headers,
                           json={"content": "First comment"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "First comment"
        assert data["card_id"] == card_id
        assert "username" in data
        assert "created_at" in data

    def test_list_comments_after_create(self, client, auth_headers, card_id):
        client.post(f"/api/cards/{card_id}/comments", headers=auth_headers,
                    json={"content": "Comment A"})
        client.post(f"/api/cards/{card_id}/comments", headers=auth_headers,
                    json={"content": "Comment B"})
        resp = client.get(f"/api/cards/{card_id}/comments", headers=auth_headers)
        assert resp.status_code == 200
        assert len(resp.json()) >= 2

    def test_delete_comment(self, client, auth_headers, card_id):
        create_resp = client.post(f"/api/cards/{card_id}/comments", headers=auth_headers,
                                  json={"content": "To delete"})
        comment_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/cards/{card_id}/comments/{comment_id}",
                                 headers=auth_headers)
        assert del_resp.status_code == 204

    def test_delete_others_comment_forbidden(self, client, auth_headers, card_id):
        """A second user should not be able to delete another user's comment."""
        import uuid
        username2 = f"user2_{uuid.uuid4().hex[:6]}"
        reg = client.post("/api/auth/register", json={"username": username2, "password": "pass123"})
        token2 = reg.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Original user posts a comment
        create_resp = client.post(f"/api/cards/{card_id}/comments", headers=auth_headers,
                                  json={"content": "Only mine"})
        comment_id = create_resp.json()["id"]

        # User 2 tries to delete it — should fail (403 or 404)
        del_resp = client.delete(f"/api/cards/{card_id}/comments/{comment_id}",
                                 headers=headers2)
        assert del_resp.status_code in (403, 404)

    def test_comment_empty_content_rejected(self, client, auth_headers, card_id):
        resp = client.post(f"/api/cards/{card_id}/comments", headers=auth_headers,
                           json={"content": "  "})
        assert resp.status_code == 400

    def test_comment_unauthenticated(self, client, card_id):
        resp = client.post(f"/api/cards/{card_id}/comments", json={"content": "hi"})
        assert resp.status_code in (401, 403)


# ── Checklist ───────────────────────────────────────────────────────────────────

class TestChecklist:
    def test_list_checklist_empty(self, client, auth_headers, card_id):
        resp = client.get(f"/api/cards/{card_id}/checklist", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_checklist_item(self, client, auth_headers, card_id):
        resp = client.post(f"/api/cards/{card_id}/checklist", headers=auth_headers,
                           json={"title": "Step 1"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Step 1"
        assert data["checked"] is False
        assert data["order"] == 0

    def test_checklist_order_increments(self, client, auth_headers, card_id):
        client.post(f"/api/cards/{card_id}/checklist", headers=auth_headers, json={"title": "A"})
        client.post(f"/api/cards/{card_id}/checklist", headers=auth_headers, json={"title": "B"})
        resp = client.get(f"/api/cards/{card_id}/checklist", headers=auth_headers)
        orders = [i["order"] for i in resp.json()]
        assert orders == sorted(orders)

    def test_update_checklist_item_checked(self, client, auth_headers, card_id):
        create_resp = client.post(f"/api/cards/{card_id}/checklist", headers=auth_headers,
                                  json={"title": "Check me"})
        item_id = create_resp.json()["id"]
        update_resp = client.put(f"/api/cards/{card_id}/checklist/{item_id}", headers=auth_headers,
                                 json={"checked": True})
        assert update_resp.status_code == 200
        assert update_resp.json()["checked"] is True

    def test_delete_checklist_item(self, client, auth_headers, card_id):
        create_resp = client.post(f"/api/cards/{card_id}/checklist", headers=auth_headers,
                                  json={"title": "Delete me"})
        item_id = create_resp.json()["id"]
        del_resp = client.delete(f"/api/cards/{card_id}/checklist/{item_id}", headers=auth_headers)
        assert del_resp.status_code == 204

    def test_checklist_item_empty_title_rejected(self, client, auth_headers, card_id):
        resp = client.post(f"/api/cards/{card_id}/checklist", headers=auth_headers,
                           json={"title": "  "})
        assert resp.status_code == 400

    def test_checklist_counts_on_board(self, client, auth_headers, seeded_board, card_id):
        """Board endpoint returns checklist_total and checklist_done."""
        client.post(f"/api/cards/{card_id}/checklist", headers=auth_headers, json={"title": "A"})
        item = client.post(f"/api/cards/{card_id}/checklist", headers=auth_headers, json={"title": "B"}).json()
        client.put(f"/api/cards/{card_id}/checklist/{item['id']}", headers=auth_headers,
                   json={"checked": True})

        board_id, _ = seeded_board
        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        card_data = board["cards"][card_id]
        assert card_data["checklist_total"] >= 2
        assert card_data["checklist_done"] >= 1


# ── Sharing ──────────────────────────────────────────────────────────────────────

class TestSharing:
    def test_list_members_empty(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        resp = client.get(f"/api/boards/{board_id}/members", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_add_and_list_member(self, client, auth_headers, seeded_board):
        import uuid
        board_id, _ = seeded_board
        username2 = f"member_{uuid.uuid4().hex[:6]}"
        client.post("/api/auth/register", json={"username": username2, "password": "pass123"})

        add_resp = client.post(f"/api/boards/{board_id}/members", headers=auth_headers,
                               json={"username": username2})
        assert add_resp.status_code == 201

        members = client.get(f"/api/boards/{board_id}/members", headers=auth_headers).json()
        assert any(m["username"] == username2 for m in members)

    def test_shared_user_can_read_board(self, client, auth_headers, seeded_board):
        import uuid
        board_id, _ = seeded_board
        username2 = f"reader_{uuid.uuid4().hex[:6]}"
        reg = client.post("/api/auth/register", json={"username": username2, "password": "pass123"})
        token2 = reg.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Share with user 2
        client.post(f"/api/boards/{board_id}/members", headers=auth_headers,
                    json={"username": username2})

        # User 2 should be able to read the board
        resp = client.get(f"/api/boards/{board_id}", headers=headers2)
        assert resp.status_code == 200

    def test_remove_member(self, client, auth_headers, seeded_board):
        import uuid
        board_id, _ = seeded_board
        username2 = f"removeme_{uuid.uuid4().hex[:6]}"
        reg = client.post("/api/auth/register", json={"username": username2, "password": "pass123"})
        user2_id = reg.json()["user_id"]

        client.post(f"/api/boards/{board_id}/members", headers=auth_headers,
                    json={"username": username2})
        del_resp = client.delete(f"/api/boards/{board_id}/members/{user2_id}",
                                 headers=auth_headers)
        assert del_resp.status_code == 204

        members = client.get(f"/api/boards/{board_id}/members", headers=auth_headers).json()
        assert not any(m["user_id"] == user2_id for m in members)

    def test_non_owner_cannot_add_member(self, client, seeded_board):
        import uuid
        board_id, _ = seeded_board
        username2 = f"intruder_{uuid.uuid4().hex[:6]}"
        reg = client.post("/api/auth/register", json={"username": username2, "password": "pass123"})
        headers2 = {"Authorization": f"Bearer {reg.json()['access_token']}"}

        resp = client.post(f"/api/boards/{board_id}/members", headers=headers2,
                           json={"username": "anyone"})
        assert resp.status_code in (403, 404)

    def test_add_nonexistent_user(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        resp = client.post(f"/api/boards/{board_id}/members", headers=auth_headers,
                           json={"username": "ghost_user_xyz_9999"})
        assert resp.status_code == 404


# ── Export ───────────────────────────────────────────────────────────────────────

class TestExport:
    def test_export_json(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        resp = client.get(f"/api/boards/{board_id}/export?format=json", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")
        data = resp.json()
        assert "board" in data
        assert "columns" in data

    def test_export_csv(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        resp = client.get(f"/api/boards/{board_id}/export?format=csv", headers=auth_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        lines = resp.text.strip().split("\n")
        assert lines[0].startswith("board,column,card_title")

    def test_export_default_is_json(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        resp = client.get(f"/api/boards/{board_id}/export", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("application/json")

    def test_export_unauthenticated(self, client, seeded_board):
        board_id, _ = seeded_board
        resp = client.get(f"/api/boards/{board_id}/export?format=json")
        assert resp.status_code in (401, 403)

    def test_export_other_users_board(self, client, seeded_board):
        import uuid
        board_id, _ = seeded_board
        username2 = f"exporter_{uuid.uuid4().hex[:6]}"
        reg = client.post("/api/auth/register", json={"username": username2, "password": "pass123"})
        headers2 = {"Authorization": f"Bearer {reg.json()['access_token']}"}
        resp = client.get(f"/api/boards/{board_id}/export?format=json", headers=headers2)
        assert resp.status_code == 404
