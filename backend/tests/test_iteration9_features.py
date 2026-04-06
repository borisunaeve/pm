"""
Tests for iteration 9 features:
  - Board favorites (POST/DELETE /api/boards/{id}/favorite, is_favorite on list)
  - Board archiving (POST /api/boards/{id}/archive, POST /api/boards/{id}/restore)
  - Archive filter on board list (include_archived param)
"""
import uuid
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_user(client, prefix="u9"):
    name = f"{prefix}_{uuid.uuid4().hex[:6]}"
    resp = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user_id"], name


def get_default_board(client, headers):
    boards = client.get("/api/boards", headers=headers).json()
    assert len(boards) >= 1
    return boards[0]["id"]


def create_board(client, headers, title="Test Board"):
    resp = client.post("/api/boards", json={"title": title}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


# ══════════════════════════════════════════════════════════════════════════════
# Board Favorites
# ══════════════════════════════════════════════════════════════════════════════

class TestBoardFavorites:
    def test_board_list_includes_is_favorite_field(self, client):
        headers, _, _ = make_user(client)
        boards = client.get("/api/boards", headers=headers).json()
        assert len(boards) >= 1
        assert "is_favorite" in boards[0]

    def test_default_not_favorite(self, client):
        headers, _, _ = make_user(client)
        boards = client.get("/api/boards", headers=headers).json()
        assert boards[0]["is_favorite"] is False

    def test_favorite_board(self, client):
        headers, _, _ = make_user(client)
        board_id = get_default_board(client, headers)
        resp = client.post(f"/api/boards/{board_id}/favorite", headers=headers)
        assert resp.status_code == 201
        assert resp.json()["status"] == "favorited"

    def test_favorited_board_reflected_in_list(self, client):
        headers, _, _ = make_user(client)
        board_id = get_default_board(client, headers)
        client.post(f"/api/boards/{board_id}/favorite", headers=headers)
        boards = client.get("/api/boards", headers=headers).json()
        board = next(b for b in boards if b["id"] == board_id)
        assert board["is_favorite"] is True

    def test_unfavorite_board(self, client):
        headers, _, _ = make_user(client)
        board_id = get_default_board(client, headers)
        client.post(f"/api/boards/{board_id}/favorite", headers=headers)
        resp = client.delete(f"/api/boards/{board_id}/favorite", headers=headers)
        assert resp.status_code == 204

    def test_unfavorited_board_reflected_in_list(self, client):
        headers, _, _ = make_user(client)
        board_id = get_default_board(client, headers)
        client.post(f"/api/boards/{board_id}/favorite", headers=headers)
        client.delete(f"/api/boards/{board_id}/favorite", headers=headers)
        boards = client.get("/api/boards", headers=headers).json()
        board = next(b for b in boards if b["id"] == board_id)
        assert board["is_favorite"] is False

    def test_favorite_idempotent(self, client):
        """Favoriting twice should not error."""
        headers, _, _ = make_user(client)
        board_id = get_default_board(client, headers)
        client.post(f"/api/boards/{board_id}/favorite", headers=headers)
        resp = client.post(f"/api/boards/{board_id}/favorite", headers=headers)
        assert resp.status_code == 201

    def test_favorites_sorted_first(self, client):
        """Favorited boards appear first in the list."""
        headers, _, _ = make_user(client)
        board_id_a = create_board(client, headers, "Board A")
        board_id_b = create_board(client, headers, "Board B")
        # Favorite B (second created)
        client.post(f"/api/boards/{board_id_b}/favorite", headers=headers)
        boards = client.get("/api/boards", headers=headers).json()
        # The first item should be the favorited one
        favorites = [b for b in boards if b["is_favorite"]]
        assert any(b["id"] == board_id_b for b in favorites)
        fav_indices = [i for i, b in enumerate(boards) if b["is_favorite"]]
        non_fav_indices = [i for i, b in enumerate(boards) if not b["is_favorite"]]
        if fav_indices and non_fav_indices:
            assert max(fav_indices) < min(non_fav_indices)

    def test_favorite_requires_auth(self, client):
        headers, _, _ = make_user(client)
        board_id = get_default_board(client, headers)
        resp = client.post(f"/api/boards/{board_id}/favorite")
        assert resp.status_code == 401

    def test_favorite_isolated_between_users(self, client):
        """User A favoriting a board doesn't affect User B's view of their own boards."""
        headers_a, _, _ = make_user(client, "u9a")
        headers_b, _, _ = make_user(client, "u9b")
        board_id_a = get_default_board(client, headers_a)
        # A favorites their board
        client.post(f"/api/boards/{board_id_a}/favorite", headers=headers_a)
        # B's boards shouldn't have that board or it shouldn't be marked as favorite
        boards_b = client.get("/api/boards", headers=headers_b).json()
        for b in boards_b:
            if b["id"] == board_id_a:
                # Shared board — favorite should only apply to the user
                assert b["is_favorite"] is False
                break

    def test_favorite_nonexistent_board(self, client):
        headers, _, _ = make_user(client)
        resp = client.post("/api/boards/nonexistent-board/favorite", headers=headers)
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Board Archiving
# ══════════════════════════════════════════════════════════════════════════════

class TestBoardArchiving:
    def test_board_list_includes_archived_field(self, client):
        headers, _, _ = make_user(client)
        boards = client.get("/api/boards", headers=headers).json()
        assert len(boards) >= 1
        assert "archived" in boards[0]

    def test_default_not_archived(self, client):
        headers, _, _ = make_user(client)
        boards = client.get("/api/boards", headers=headers).json()
        assert boards[0]["archived"] is False

    def test_archive_board(self, client):
        headers, _, _ = make_user(client)
        board_id = create_board(client, headers, "To Archive")
        resp = client.post(f"/api/boards/{board_id}/archive", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

    def test_archived_board_hidden_from_default_list(self, client):
        headers, _, _ = make_user(client)
        board_id = create_board(client, headers, "Will Archive")
        client.post(f"/api/boards/{board_id}/archive", headers=headers)
        boards = client.get("/api/boards", headers=headers).json()
        ids = [b["id"] for b in boards]
        assert board_id not in ids

    def test_archived_board_shown_with_flag(self, client):
        headers, _, _ = make_user(client)
        board_id = create_board(client, headers, "Archived Board")
        client.post(f"/api/boards/{board_id}/archive", headers=headers)
        boards = client.get("/api/boards?include_archived=true", headers=headers).json()
        ids = [b["id"] for b in boards]
        assert board_id in ids

    def test_archived_board_marked_in_response(self, client):
        headers, _, _ = make_user(client)
        board_id = create_board(client, headers, "Mark Archived")
        client.post(f"/api/boards/{board_id}/archive", headers=headers)
        boards = client.get("/api/boards?include_archived=true", headers=headers).json()
        board = next((b for b in boards if b["id"] == board_id), None)
        assert board is not None
        assert board["archived"] is True

    def test_restore_board(self, client):
        headers, _, _ = make_user(client)
        board_id = create_board(client, headers, "Restore Me")
        client.post(f"/api/boards/{board_id}/archive", headers=headers)
        resp = client.post(f"/api/boards/{board_id}/restore", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "restored"

    def test_restored_board_appears_in_default_list(self, client):
        headers, _, _ = make_user(client)
        board_id = create_board(client, headers, "Back from Archive")
        client.post(f"/api/boards/{board_id}/archive", headers=headers)
        client.post(f"/api/boards/{board_id}/restore", headers=headers)
        boards = client.get("/api/boards", headers=headers).json()
        ids = [b["id"] for b in boards]
        assert board_id in ids

    def test_restored_board_not_archived(self, client):
        headers, _, _ = make_user(client)
        board_id = create_board(client, headers, "Restored")
        client.post(f"/api/boards/{board_id}/archive", headers=headers)
        client.post(f"/api/boards/{board_id}/restore", headers=headers)
        boards = client.get("/api/boards", headers=headers).json()
        board = next((b for b in boards if b["id"] == board_id), None)
        assert board is not None
        assert board["archived"] is False

    def test_archive_requires_owner(self, client):
        """Non-owner member cannot archive a board."""
        headers_owner, _, _ = make_user(client, "u9ow")
        headers_member, _, member_name = make_user(client, "u9mb")
        board_id = get_default_board(client, headers_owner)
        # Share with member
        client.post(f"/api/boards/{board_id}/members", json={"username": member_name}, headers=headers_owner)
        resp = client.post(f"/api/boards/{board_id}/archive", headers=headers_member)
        assert resp.status_code == 404

    def test_archive_requires_auth(self, client):
        headers, _, _ = make_user(client)
        board_id = get_default_board(client, headers)
        resp = client.post(f"/api/boards/{board_id}/archive")
        assert resp.status_code == 401

    def test_restore_requires_auth(self, client):
        headers, _, _ = make_user(client)
        board_id = get_default_board(client, headers)
        resp = client.post(f"/api/boards/{board_id}/restore")
        assert resp.status_code == 401

    def test_archive_nonexistent_board(self, client):
        headers, _, _ = make_user(client)
        resp = client.post("/api/boards/no-such-board/archive", headers=headers)
        assert resp.status_code == 404

    def test_multiple_archived_boards_all_shown(self, client):
        headers, _, _ = make_user(client)
        b1 = create_board(client, headers, "Archive 1")
        b2 = create_board(client, headers, "Archive 2")
        client.post(f"/api/boards/{b1}/archive", headers=headers)
        client.post(f"/api/boards/{b2}/archive", headers=headers)
        boards = client.get("/api/boards?include_archived=true", headers=headers).json()
        archived_ids = {b["id"] for b in boards if b["archived"]}
        assert b1 in archived_ids
        assert b2 in archived_ids
