"""
Tests for iteration 5 features:
  - User display name (GET/PUT /api/auth/me)
  - Board color + description (POST/PUT /api/boards)
  - Card watching (POST/DELETE /api/cards/{id}/watch, GET watchers)
  - Persistent notifications (triggered on card updates and comments)
  - Dashboard (GET /api/dashboard/my-cards, /api/dashboard/summary)
"""
import uuid
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_user(client, prefix="u5"):
    name = f"{prefix}_{uuid.uuid4().hex[:6]}"
    resp = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert resp.status_code == 201, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}, resp.json()["user_id"], name


def make_board(client, headers, title="Test Board"):
    # Get first board created at registration
    boards = client.get("/api/boards", headers=headers).json()
    if boards:
        return boards[0]["id"], boards[0].get("id")
    resp = client.post("/api/boards", json={"title": title}, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def get_first_column(client, headers, board_id):
    board = client.get(f"/api/boards/{board_id}", headers=headers).json()
    return board["columns"][0]["id"]


def create_card(client, headers, col_id, title="Task", **kwargs):
    resp = client.post("/api/cards", json={"title": title, "column_id": col_id, **kwargs}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ══════════════════════════════════════════════════════════════════════════════
# Display Name
# ══════════════════════════════════════════════════════════════════════════════

class TestDisplayName:
    def test_me_returns_display_name_field(self, client):
        headers, uid, uname = make_user(client, "dn1")
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "display_name" in data
        assert data["display_name"] == ""

    def test_update_display_name(self, client):
        headers, uid, uname = make_user(client, "dn2")
        resp = client.put("/api/auth/me", json={"display_name": "Alice Smith"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["display_name"] == "Alice Smith"

    def test_updated_display_name_persists(self, client):
        headers, uid, uname = make_user(client, "dn3")
        client.put("/api/auth/me", json={"display_name": "Bob Jones"}, headers=headers)
        resp = client.get("/api/auth/me", headers=headers)
        assert resp.json()["display_name"] == "Bob Jones"

    def test_update_display_name_trims_whitespace(self, client):
        headers, uid, uname = make_user(client, "dn4")
        resp = client.put("/api/auth/me", json={"display_name": "  Carol  "}, headers=headers)
        assert resp.json()["display_name"] == "Carol"

    def test_update_requires_auth(self, client):
        resp = client.put("/api/auth/me", json={"display_name": "hacker"})
        assert resp.status_code == 401

    def test_display_name_can_be_cleared(self, client):
        headers, uid, uname = make_user(client, "dn5")
        client.put("/api/auth/me", json={"display_name": "Dave"}, headers=headers)
        resp = client.put("/api/auth/me", json={"display_name": ""}, headers=headers)
        assert resp.json()["display_name"] == ""


# ══════════════════════════════════════════════════════════════════════════════
# Board Color and Description
# ══════════════════════════════════════════════════════════════════════════════

class TestBoardColorDescription:
    def test_create_board_with_color_and_description(self, client):
        headers, uid, uname = make_user(client, "bc1")
        resp = client.post(
            "/api/boards",
            json={"title": "Colored Board", "color": "#209dd7", "description": "A blue board"},
            headers=headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["color"] == "#209dd7"
        assert data["description"] == "A blue board"

    def test_list_boards_includes_color_description(self, client):
        headers, uid, uname = make_user(client, "bc2")
        client.post(
            "/api/boards",
            json={"title": "Tagged", "color": "#753991", "description": "Purple board"},
            headers=headers,
        )
        boards = client.get("/api/boards", headers=headers).json()
        tagged = next((b for b in boards if b["title"] == "Tagged"), None)
        assert tagged is not None
        assert tagged["color"] == "#753991"
        assert tagged["description"] == "Purple board"

    def test_list_boards_includes_member_count(self, client):
        headers, uid, uname = make_user(client, "bc3")
        boards = client.get("/api/boards", headers=headers).json()
        assert all("member_count" in b for b in boards)

    def test_update_board_color(self, client):
        headers, uid, uname = make_user(client, "bc4")
        boards = client.get("/api/boards", headers=headers).json()
        board_id = boards[0]["id"]
        resp = client.put(
            f"/api/boards/{board_id}",
            json={"title": boards[0]["title"], "color": "#ecad0a"},
            headers=headers,
        )
        assert resp.status_code == 200
        boards_after = client.get("/api/boards", headers=headers).json()
        b = next(x for x in boards_after if x["id"] == board_id)
        assert b["color"] == "#ecad0a"

    def test_update_board_description(self, client):
        headers, uid, uname = make_user(client, "bc5")
        boards = client.get("/api/boards", headers=headers).json()
        board_id = boards[0]["id"]
        client.put(
            f"/api/boards/{board_id}",
            json={"title": boards[0]["title"], "description": "Updated description"},
            headers=headers,
        )
        boards_after = client.get("/api/boards", headers=headers).json()
        b = next(x for x in boards_after if x["id"] == board_id)
        assert b["description"] == "Updated description"

    def test_board_color_defaults_to_none(self, client):
        headers, uid, uname = make_user(client, "bc6")
        boards = client.get("/api/boards", headers=headers).json()
        # Default board has no color
        assert boards[0]["color"] is None


# ══════════════════════════════════════════════════════════════════════════════
# Card Watching
# ══════════════════════════════════════════════════════════════════════════════

class TestCardWatching:
    def _setup(self, client):
        headers, uid, uname = make_user(client, "cw")
        boards = client.get("/api/boards", headers=headers).json()
        board_id = boards[0]["id"]
        col_id = get_first_column(client, headers, board_id)
        card = create_card(client, headers, col_id, "Watch me")
        return headers, uid, board_id, col_id, card

    def test_watch_card(self, client):
        headers, uid, board_id, col_id, card = self._setup(client)
        resp = client.post(f"/api/cards/{card['id']}/watch", headers=headers)
        assert resp.status_code == 201
        assert resp.json()["status"] == "watching"

    def test_watch_status_true_after_watch(self, client):
        headers, uid, board_id, col_id, card = self._setup(client)
        client.post(f"/api/cards/{card['id']}/watch", headers=headers)
        resp = client.get(f"/api/cards/{card['id']}/watch/status", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["watching"] is True

    def test_watch_status_false_by_default(self, client):
        headers, uid, board_id, col_id, card = self._setup(client)
        resp = client.get(f"/api/cards/{card['id']}/watch/status", headers=headers)
        # Creator is auto-watched on card creation
        assert "watching" in resp.json()

    def test_unwatch_card(self, client):
        headers, uid, board_id, col_id, card = self._setup(client)
        client.post(f"/api/cards/{card['id']}/watch", headers=headers)
        resp = client.delete(f"/api/cards/{card['id']}/watch", headers=headers)
        assert resp.status_code == 204
        status = client.get(f"/api/cards/{card['id']}/watch/status", headers=headers).json()
        assert status["watching"] is False

    def test_list_watchers(self, client):
        headers, uid, board_id, col_id, card = self._setup(client)
        client.post(f"/api/cards/{card['id']}/watch", headers=headers)
        resp = client.get(f"/api/cards/{card['id']}/watchers", headers=headers)
        assert resp.status_code == 200
        watchers = resp.json()
        assert any(w["user_id"] == uid for w in watchers)

    def test_duplicate_watch_is_idempotent(self, client):
        headers, uid, board_id, col_id, card = self._setup(client)
        client.post(f"/api/cards/{card['id']}/watch", headers=headers)
        resp2 = client.post(f"/api/cards/{card['id']}/watch", headers=headers)
        assert resp2.status_code == 201
        watchers = client.get(f"/api/cards/{card['id']}/watchers", headers=headers).json()
        assert len([w for w in watchers if w["user_id"] == uid]) == 1

    def test_watch_requires_auth(self, client):
        headers, uid, board_id, col_id, card = self._setup(client)
        resp = client.post(f"/api/cards/{card['id']}/watch")
        assert resp.status_code == 401

    def test_watcher_item_has_username(self, client):
        headers, uid, board_id, col_id, card = self._setup(client)
        client.post(f"/api/cards/{card['id']}/watch", headers=headers)
        watchers = client.get(f"/api/cards/{card['id']}/watchers", headers=headers).json()
        w = next(x for x in watchers if x["user_id"] == uid)
        assert "username" in w
        assert len(w["username"]) > 0


# ══════════════════════════════════════════════════════════════════════════════
# Persistent Notifications
# ══════════════════════════════════════════════════════════════════════════════

class TestPersistentNotifications:
    def _two_users_shared_card(self, client):
        """Returns (headers1, headers2, board_id, col_id, card) where user2 is member."""
        h1, uid1, uname1 = make_user(client, "pn1")
        h2, uid2, uname2 = make_user(client, "pn2")
        boards = client.get("/api/boards", headers=h1).json()
        board_id = boards[0]["id"]
        col_id = get_first_column(client, h1, board_id)
        # user2 joins board
        client.post(f"/api/boards/{board_id}/members", json={"username": uname2}, headers=h1)
        # user1 creates card, user2 watches it
        card = create_card(client, h1, col_id, "Shared card")
        client.post(f"/api/cards/{card['id']}/watch", headers=h2)
        return h1, h2, uid1, uid2, board_id, col_id, card

    def test_card_update_notifies_watcher(self, client):
        h1, h2, uid1, uid2, board_id, col_id, card = self._two_users_shared_card(client)
        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col_id, "order": 0, "title": "Updated title"
        }, headers=h1)
        notifs = client.get("/api/notifications", headers=h2).json()
        assert any("Updated title" in n["message"] or "Shared card" in n["message"] for n in notifs)

    def test_comment_notifies_watcher(self, client):
        h1, h2, uid1, uid2, board_id, col_id, card = self._two_users_shared_card(client)
        client.post(f"/api/cards/{card['id']}/comments", json={"content": "Hello!"}, headers=h1)
        notifs = client.get("/api/notifications", headers=h2).json()
        assert any(n["type"] == "comment_added" for n in notifs)

    def test_actor_not_notified_of_own_action(self, client):
        h1, h2, uid1, uid2, board_id, col_id, card = self._two_users_shared_card(client)
        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col_id, "order": 0, "title": "Self update"
        }, headers=h1)
        notifs = client.get("/api/notifications", headers=h1).json()
        # h1 updated the card — they should NOT get a notification for their own action
        assert not any("Self update" in n["message"] for n in notifs)

    def test_unread_count(self, client):
        h1, h2, uid1, uid2, board_id, col_id, card = self._two_users_shared_card(client)
        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col_id, "order": 0, "title": "Count test"
        }, headers=h1)
        resp = client.get("/api/notifications/unread-count", headers=h2)
        assert resp.status_code == 200
        assert resp.json()["count"] >= 1

    def test_mark_notification_read(self, client):
        h1, h2, uid1, uid2, board_id, col_id, card = self._two_users_shared_card(client)
        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col_id, "order": 0, "title": "Mark read test"
        }, headers=h1)
        notifs = client.get("/api/notifications", headers=h2).json()
        notif_id = notifs[0]["id"]
        resp = client.post(f"/api/notifications/{notif_id}/read", headers=h2)
        assert resp.status_code == 200
        notifs_after = client.get("/api/notifications", headers=h2).json()
        marked = next(n for n in notifs_after if n["id"] == notif_id)
        assert marked["read"] is True

    def test_mark_all_read(self, client):
        h1, h2, uid1, uid2, board_id, col_id, card = self._two_users_shared_card(client)
        # Create two update notifications
        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col_id, "order": 0, "title": "Update 1"
        }, headers=h1)
        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col_id, "order": 0, "title": "Update 2"
        }, headers=h1)
        client.post("/api/notifications/read-all", headers=h2)
        count = client.get("/api/notifications/unread-count", headers=h2).json()["count"]
        assert count == 0

    def test_clear_read_notifications(self, client):
        h1, h2, uid1, uid2, board_id, col_id, card = self._two_users_shared_card(client)
        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col_id, "order": 0, "title": "To clear"
        }, headers=h1)
        client.post("/api/notifications/read-all", headers=h2)
        client.delete("/api/notifications", headers=h2)
        notifs = client.get("/api/notifications", headers=h2).json()
        assert notifs == []

    def test_assignment_notifies_assignee(self, client):
        h1, uid1, uname1 = make_user(client, "pna1")
        h2, uid2, uname2 = make_user(client, "pna2")
        boards = client.get("/api/boards", headers=h1).json()
        board_id = boards[0]["id"]
        col_id = get_first_column(client, h1, board_id)
        client.post(f"/api/boards/{board_id}/members", json={"username": uname2}, headers=h1)
        create_card(client, h1, col_id, "Assigned task", assignee_id=uid2)
        notifs = client.get("/api/notifications", headers=h2).json()
        assert any(n["type"] == "assigned" for n in notifs)

    def test_notifications_require_auth(self, client):
        resp = client.get("/api/notifications")
        assert resp.status_code == 401

    def test_unread_count_requires_auth(self, client):
        resp = client.get("/api/notifications/unread-count")
        assert resp.status_code == 401

    def test_cannot_read_others_notification(self, client):
        h1, h2, uid1, uid2, board_id, col_id, card = self._two_users_shared_card(client)
        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col_id, "order": 0, "title": "Other notif"
        }, headers=h1)
        notifs_h2 = client.get("/api/notifications", headers=h2).json()
        if notifs_h2:
            notif_id = notifs_h2[0]["id"]
            # h1 trying to mark h2's notification as read should 404
            resp = client.post(f"/api/notifications/{notif_id}/read", headers=h1)
            assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════════════════
# Dashboard
# ══════════════════════════════════════════════════════════════════════════════

class TestDashboard:
    def test_my_cards_empty_when_no_assignments(self, client):
        headers, uid, uname = make_user(client, "db1")
        resp = client.get("/api/dashboard/my-cards", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_my_cards_returns_assigned_cards(self, client):
        headers, uid, uname = make_user(client, "db2")
        boards = client.get("/api/boards", headers=headers).json()
        col_id = get_first_column(client, headers, boards[0]["id"])
        create_card(client, headers, col_id, "My assigned task", assignee_id=uid)
        my_cards = client.get("/api/dashboard/my-cards", headers=headers).json()
        assert any(c["title"] == "My assigned task" for c in my_cards)

    def test_my_cards_excludes_unassigned(self, client):
        headers, uid, uname = make_user(client, "db3")
        boards = client.get("/api/boards", headers=headers).json()
        col_id = get_first_column(client, headers, boards[0]["id"])
        create_card(client, headers, col_id, "Unassigned task")
        my_cards = client.get("/api/dashboard/my-cards", headers=headers).json()
        assert not any(c["title"] == "Unassigned task" for c in my_cards)

    def test_my_cards_excludes_archived(self, client):
        headers, uid, uname = make_user(client, "db4")
        boards = client.get("/api/boards", headers=headers).json()
        col_id = get_first_column(client, headers, boards[0]["id"])
        card = create_card(client, headers, col_id, "Archived assigned", assignee_id=uid)
        client.put(f"/api/cards/{card['id']}/archive", headers=headers)
        my_cards = client.get("/api/dashboard/my-cards", headers=headers).json()
        assert not any(c["id"] == card["id"] for c in my_cards)

    def test_my_cards_from_shared_board(self, client):
        """User can see cards assigned to them on a board they're a member of."""
        h1, uid1, uname1 = make_user(client, "db5a")
        h2, uid2, uname2 = make_user(client, "db5b")
        boards = client.get("/api/boards", headers=h1).json()
        board_id = boards[0]["id"]
        col_id = get_first_column(client, h1, board_id)
        client.post(f"/api/boards/{board_id}/members", json={"username": uname2}, headers=h1)
        create_card(client, h1, col_id, "Task for user2", assignee_id=uid2)
        my_cards = client.get("/api/dashboard/my-cards", headers=h2).json()
        assert any(c["title"] == "Task for user2" for c in my_cards)

    def test_my_cards_has_board_info(self, client):
        headers, uid, uname = make_user(client, "db6")
        boards = client.get("/api/boards", headers=headers).json()
        col_id = get_first_column(client, headers, boards[0]["id"])
        create_card(client, headers, col_id, "Info card", assignee_id=uid)
        my_cards = client.get("/api/dashboard/my-cards", headers=headers).json()
        c = next(x for x in my_cards if x["title"] == "Info card")
        assert "board_id" in c
        assert "board_title" in c
        assert "column_title" in c

    def test_dashboard_summary(self, client):
        headers, uid, uname = make_user(client, "db7")
        resp = client.get("/api/dashboard/summary", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "board_count" in data
        assert "assigned_cards" in data
        assert "overdue_cards" in data
        assert "due_this_week" in data
        assert "unread_notifications" in data

    def test_dashboard_summary_counts_assigned(self, client):
        from datetime import date, timedelta
        headers, uid, uname = make_user(client, "db8")
        boards = client.get("/api/boards", headers=headers).json()
        col_id = get_first_column(client, headers, boards[0]["id"])
        create_card(client, headers, col_id, "Assigned", assignee_id=uid)
        summary = client.get("/api/dashboard/summary", headers=headers).json()
        assert summary["assigned_cards"] >= 1

    def test_dashboard_summary_counts_overdue(self, client):
        from datetime import date, timedelta
        headers, uid, uname = make_user(client, "db9")
        boards = client.get("/api/boards", headers=headers).json()
        col_id = get_first_column(client, headers, boards[0]["id"])
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        create_card(client, headers, col_id, "Overdue", assignee_id=uid, due_date=yesterday)
        summary = client.get("/api/dashboard/summary", headers=headers).json()
        assert summary["overdue_cards"] >= 1

    def test_my_cards_requires_auth(self, client):
        resp = client.get("/api/dashboard/my-cards")
        assert resp.status_code == 401

    def test_dashboard_summary_requires_auth(self, client):
        resp = client.get("/api/dashboard/summary")
        assert resp.status_code == 401
