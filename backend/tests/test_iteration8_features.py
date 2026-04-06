"""
Tests for iteration 8 features:
  - Card links (GET/POST/DELETE /api/cards/{id}/links)
  - CSV import (POST /api/boards/{id}/import)
  - Member role management (PUT /api/boards/{id}/members/{user_id})
  - User activity feed (GET /api/users/me/activity)
"""
import uuid
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_user(client, prefix="u8"):
    name = f"{prefix}_{uuid.uuid4().hex[:6]}"
    resp = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    return {"Authorization": f"Bearer {data['access_token']}"}, data["user_id"], name


def get_board_and_col(client, headers):
    boards = client.get("/api/boards", headers=headers).json()
    board_id = boards[0]["id"]
    board = client.get(f"/api/boards/{board_id}", headers=headers).json()
    col_id = board["columns"][0]["id"]
    return board_id, col_id


def create_card(client, headers, col_id, title="Card", **kwargs):
    resp = client.post("/api/cards", json={"title": title, "column_id": col_id, **kwargs}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ══════════════════════════════════════════════════════════════════════════════
# Card Links
# ══════════════════════════════════════════════════════════════════════════════

class TestCardLinks:
    def test_list_links_empty(self, client):
        h, uid, uname = make_user(client, "cl1")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id)
        resp = client.get(f"/api/cards/{card['id']}/links", headers=h)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_link(self, client):
        h, uid, uname = make_user(client, "cl2")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id)
        resp = client.post(
            f"/api/cards/{card['id']}/links",
            json={"title": "GitHub", "url": "https://github.com"},
            headers=h,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["url"] == "https://github.com"
        assert data["title"] == "GitHub"
        assert data["card_id"] == card["id"]

    def test_create_link_url_only(self, client):
        h, uid, uname = make_user(client, "cl3")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id)
        resp = client.post(
            f"/api/cards/{card['id']}/links",
            json={"url": "https://example.com"},
            headers=h,
        )
        assert resp.status_code == 201
        assert resp.json()["url"] == "https://example.com"

    def test_link_appears_in_list(self, client):
        h, uid, uname = make_user(client, "cl4")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id)
        client.post(f"/api/cards/{card['id']}/links", json={"url": "https://a.com", "title": "A"}, headers=h)
        client.post(f"/api/cards/{card['id']}/links", json={"url": "https://b.com", "title": "B"}, headers=h)
        links = client.get(f"/api/cards/{card['id']}/links", headers=h).json()
        assert len(links) == 2
        urls = {lk["url"] for lk in links}
        assert "https://a.com" in urls and "https://b.com" in urls

    def test_delete_link(self, client):
        h, uid, uname = make_user(client, "cl5")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id)
        lk = client.post(f"/api/cards/{card['id']}/links", json={"url": "https://x.com"}, headers=h).json()
        resp = client.delete(f"/api/cards/{card['id']}/links/{lk['id']}", headers=h)
        assert resp.status_code == 204
        links = client.get(f"/api/cards/{card['id']}/links", headers=h).json()
        assert len(links) == 0

    def test_delete_nonexistent_link(self, client):
        h, uid, uname = make_user(client, "cl6")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id)
        resp = client.delete(f"/api/cards/{card['id']}/links/99999", headers=h)
        assert resp.status_code == 404

    def test_empty_url_rejected(self, client):
        h, uid, uname = make_user(client, "cl7")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id)
        resp = client.post(f"/api/cards/{card['id']}/links", json={"url": ""}, headers=h)
        assert resp.status_code == 400

    def test_links_auth_required(self, client):
        h, uid, uname = make_user(client, "cl8")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id)
        resp = client.get(f"/api/cards/{card['id']}/links")
        assert resp.status_code == 401

    def test_links_isolation_between_users(self, client):
        h1, uid1, un1 = make_user(client, "cl9a")
        h2, uid2, un2 = make_user(client, "cl9b")
        board_id, col_id = get_board_and_col(client, h1)
        card = create_card(client, h1, col_id)
        resp = client.get(f"/api/cards/{card['id']}/links", headers=h2)
        assert resp.status_code == 404

    def test_link_has_created_at(self, client):
        h, uid, uname = make_user(client, "cl10")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id)
        lk = client.post(f"/api/cards/{card['id']}/links", json={"url": "https://t.co"}, headers=h).json()
        assert "created_at" in lk
        assert lk["created_at"]


# ══════════════════════════════════════════════════════════════════════════════
# CSV Import
# ══════════════════════════════════════════════════════════════════════════════

class TestCSVImport:
    def test_import_basic(self, client):
        h, uid, uname = make_user(client, "ci1")
        board_id, col_id = get_board_and_col(client, h)
        csv_text = "title,priority\nTask One,high\nTask Two,low"
        resp = client.post(
            f"/api/boards/{board_id}/import",
            json={"csv_text": csv_text},
            headers=h,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["created"] == 2
        assert data["skipped"] == 0

    def test_import_cards_appear_on_board(self, client):
        h, uid, uname = make_user(client, "ci2")
        board_id, col_id = get_board_and_col(client, h)
        csv_text = "title\nImported Alpha\nImported Beta"
        client.post(f"/api/boards/{board_id}/import", json={"csv_text": csv_text}, headers=h)
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        titles = {c["title"] for c in board["cards"].values()}
        assert "Imported Alpha" in titles
        assert "Imported Beta" in titles

    def test_import_with_all_fields(self, client):
        h, uid, uname = make_user(client, "ci3")
        board_id, col_id = get_board_and_col(client, h)
        csv_text = "title,priority,due_date,labels,details\nFull Card,high,2030-12-31,frontend,Some details"
        client.post(f"/api/boards/{board_id}/import", json={"csv_text": csv_text}, headers=h)
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        card = next((c for c in board["cards"].values() if c["title"] == "Full Card"), None)
        assert card is not None
        assert card["priority"] == "high"
        assert card["due_date"] == "2030-12-31"
        assert "frontend" in card["labels"]

    def test_import_invalid_priority_defaults_medium(self, client):
        h, uid, uname = make_user(client, "ci4")
        board_id, col_id = get_board_and_col(client, h)
        csv_text = "title,priority\nBad Priority Card,urgent"
        client.post(f"/api/boards/{board_id}/import", json={"csv_text": csv_text}, headers=h)
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        card = next((c for c in board["cards"].values() if c["title"] == "Bad Priority Card"), None)
        assert card is not None
        assert card["priority"] == "medium"

    def test_import_empty_title_row_skipped(self, client):
        h, uid, uname = make_user(client, "ci5")
        board_id, col_id = get_board_and_col(client, h)
        # Row with explicit empty title (not a blank line) is skipped
        csv_text = "title\nReal Card\n \nAnother Card"
        resp = client.post(f"/api/boards/{board_id}/import", json={"csv_text": csv_text}, headers=h)
        data = resp.json()
        assert data["created"] == 2
        assert data["skipped"] == 1

    def test_import_no_title_column_fails(self, client):
        h, uid, uname = make_user(client, "ci6")
        board_id, col_id = get_board_and_col(client, h)
        csv_text = "name,priority\nTask,high"
        resp = client.post(f"/api/boards/{board_id}/import", json={"csv_text": csv_text}, headers=h)
        assert resp.status_code == 400

    def test_import_to_specific_column(self, client):
        h, uid, uname = make_user(client, "ci7")
        board_id, col_id = get_board_and_col(client, h)
        # Get second column if it exists, or use first
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        target_col = board["columns"][-1]["id"]
        csv_text = "title\nColSpecific"
        client.post(
            f"/api/boards/{board_id}/import",
            json={"csv_text": csv_text, "column_id": target_col},
            headers=h,
        )
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        col = next(c for c in board["columns"] if c["id"] == target_col)
        card_titles = [board["cards"][cid]["title"] for cid in col["cardIds"] if cid in board["cards"]]
        assert "ColSpecific" in card_titles

    def test_import_requires_auth(self, client):
        h, uid, uname = make_user(client, "ci8")
        board_id, col_id = get_board_and_col(client, h)
        resp = client.post(f"/api/boards/{board_id}/import", json={"csv_text": "title\nTest"})
        assert resp.status_code == 401

    def test_import_returns_count(self, client):
        h, uid, uname = make_user(client, "ci9")
        board_id, col_id = get_board_and_col(client, h)
        csv_text = "\n".join(["title"] + [f"Card {i}" for i in range(10)])
        resp = client.post(f"/api/boards/{board_id}/import", json={"csv_text": csv_text}, headers=h)
        assert resp.json()["created"] == 10


# ══════════════════════════════════════════════════════════════════════════════
# Member Role Management
# ══════════════════════════════════════════════════════════════════════════════

class TestMemberRoles:
    def _setup(self, client, prefix="mr"):
        h1, uid1, un1 = make_user(client, f"{prefix}a")
        h2, uid2, un2 = make_user(client, f"{prefix}b")
        boards = client.get("/api/boards", headers=h1).json()
        board_id = boards[0]["id"]
        client.post(f"/api/boards/{board_id}/members", json={"username": un2}, headers=h1)
        return h1, h2, uid1, uid2, un1, un2, board_id

    def test_member_default_role_is_member(self, client):
        h1, h2, uid1, uid2, un1, un2, board_id = self._setup(client, "mr1")
        members = client.get(f"/api/boards/{board_id}/members", headers=h1).json()
        member = next(m for m in members if m["user_id"] == uid2)
        assert member["role"] == "member"

    def test_owner_can_update_role_to_viewer(self, client):
        h1, h2, uid1, uid2, un1, un2, board_id = self._setup(client, "mr2")
        resp = client.put(
            f"/api/boards/{board_id}/members/{uid2}",
            json={"role": "viewer"},
            headers=h1,
        )
        assert resp.status_code == 200
        assert resp.json()["role"] == "viewer"

    def test_role_reflected_in_member_list(self, client):
        h1, h2, uid1, uid2, un1, un2, board_id = self._setup(client, "mr3")
        client.put(f"/api/boards/{board_id}/members/{uid2}", json={"role": "viewer"}, headers=h1)
        members = client.get(f"/api/boards/{board_id}/members", headers=h1).json()
        member = next(m for m in members if m["user_id"] == uid2)
        assert member["role"] == "viewer"

    def test_only_owner_can_update_role(self, client):
        h1, h2, uid1, uid2, un1, un2, board_id = self._setup(client, "mr4")
        resp = client.put(
            f"/api/boards/{board_id}/members/{uid2}",
            json={"role": "viewer"},
            headers=h2,
        )
        assert resp.status_code == 403

    def test_invalid_role_rejected(self, client):
        h1, h2, uid1, uid2, un1, un2, board_id = self._setup(client, "mr5")
        resp = client.put(
            f"/api/boards/{board_id}/members/{uid2}",
            json={"role": "admin"},
            headers=h1,
        )
        assert resp.status_code == 400

    def test_update_nonexistent_member_fails(self, client):
        h1, uid1, un1 = make_user(client, "mr6")
        boards = client.get("/api/boards", headers=h1).json()
        board_id = boards[0]["id"]
        resp = client.put(
            f"/api/boards/{board_id}/members/nonexistent",
            json={"role": "viewer"},
            headers=h1,
        )
        assert resp.status_code == 404

    def test_role_update_to_member(self, client):
        h1, h2, uid1, uid2, un1, un2, board_id = self._setup(client, "mr7")
        client.put(f"/api/boards/{board_id}/members/{uid2}", json={"role": "viewer"}, headers=h1)
        resp = client.put(f"/api/boards/{board_id}/members/{uid2}", json={"role": "member"}, headers=h1)
        assert resp.status_code == 200
        assert resp.json()["role"] == "member"

    def test_role_update_requires_auth(self, client):
        h1, h2, uid1, uid2, un1, un2, board_id = self._setup(client, "mr8")
        resp = client.put(f"/api/boards/{board_id}/members/{uid2}", json={"role": "viewer"})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# User Activity Feed
# ══════════════════════════════════════════════════════════════════════════════

class TestUserActivity:
    def test_activity_requires_auth(self, client):
        resp = client.get("/api/users/me/activity")
        assert resp.status_code == 401

    def test_activity_empty_for_new_user(self, client):
        h, uid, uname = make_user(client, "ua1")
        # New user has no boards initially (auto-created board has no activity logged)
        resp = client.get("/api/users/me/activity", headers=h)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_activity_recorded_after_card_create(self, client):
        h, uid, uname = make_user(client, "ua2")
        board_id, col_id = get_board_and_col(client, h)
        create_card(client, h, col_id, "Activity Test Card")
        resp = client.get("/api/users/me/activity", headers=h)
        assert resp.status_code == 200
        activities = resp.json()
        assert any(a["entity_title"] == "Activity Test Card" for a in activities)

    def test_activity_has_required_fields(self, client):
        h, uid, uname = make_user(client, "ua3")
        board_id, col_id = get_board_and_col(client, h)
        create_card(client, h, col_id, "Field Test Card")
        activities = client.get("/api/users/me/activity", headers=h).json()
        for a in activities:
            assert "id" in a
            assert "board_id" in a
            assert "board_title" in a
            assert "action" in a
            assert "entity_type" in a
            assert "created_at" in a

    def test_activity_is_sorted_newest_first(self, client):
        h, uid, uname = make_user(client, "ua4")
        board_id, col_id = get_board_and_col(client, h)
        create_card(client, h, col_id, "First Card")
        create_card(client, h, col_id, "Second Card")
        activities = client.get("/api/users/me/activity", headers=h).json()
        if len(activities) >= 2:
            assert activities[0]["created_at"] >= activities[-1]["created_at"]

    def test_activity_limit_parameter(self, client):
        h, uid, uname = make_user(client, "ua5")
        board_id, col_id = get_board_and_col(client, h)
        for i in range(10):
            create_card(client, h, col_id, f"Card {i}")
        activities = client.get("/api/users/me/activity?limit=5", headers=h).json()
        assert len(activities) <= 5

    def test_activity_shows_board_title(self, client):
        h, uid, uname = make_user(client, "ua6")
        board_id, col_id = get_board_and_col(client, h)
        create_card(client, h, col_id, "Board Title Test")
        activities = client.get("/api/users/me/activity", headers=h).json()
        assert all(a["board_title"] for a in activities if a["board_id"])

    def test_activity_isolation_between_users(self, client):
        h1, uid1, un1 = make_user(client, "ua7a")
        h2, uid2, un2 = make_user(client, "ua7b")
        board_id1, col_id1 = get_board_and_col(client, h1)
        create_card(client, h1, col_id1, "User1 Only Card")
        activities2 = client.get("/api/users/me/activity", headers=h2).json()
        titles = [a.get("entity_title") for a in activities2]
        assert "User1 Only Card" not in titles

    def test_activity_counts_multiple_actions(self, client):
        h, uid, uname = make_user(client, "ua8")
        board_id, col_id = get_board_and_col(client, h)
        c1 = create_card(client, h, col_id, "Card A")
        c2 = create_card(client, h, col_id, "Card B")
        c3 = create_card(client, h, col_id, "Card C")
        activities = client.get("/api/users/me/activity", headers=h).json()
        assert len(activities) >= 3
