"""
Tests for:
  - Card activity/audit log (GET /api/cards/{id}/activity)
  - Notifications (GET /api/notifications)
  - Bulk operations (POST /api/cards/bulk/archive, /bulk/update)
  - Board templates (POST /api/boards with template param)
"""
import pytest
from datetime import date, timedelta


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_user(client, prefix="u"):
    import uuid
    name = f"{prefix}_{uuid.uuid4().hex[:6]}"
    resp = client.post("/api/auth/register", json={"username": name, "password": "pass1234"})
    assert resp.status_code == 201
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_card(client, headers, col_id, title="Test card", **kwargs):
    resp = client.post("/api/cards", json={"title": title, "column_id": col_id, **kwargs}, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def get_board(client, headers, board_id):
    return client.get(f"/api/boards/{board_id}", headers=headers).json()


# ══════════════════════════════════════════════════════════════════════════════
# Card Activity
# ══════════════════════════════════════════════════════════════════════════════

class TestCardActivity:
    def test_empty_initially(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id)
        resp = client.get(f"/api/cards/{card['id']}/activity", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_update_title_logs_activity(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id, "Original title")

        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col_id, "order": 0,
            "title": "Changed title",
        }, headers=auth_headers)

        resp = client.get(f"/api/cards/{card['id']}/activity", headers=auth_headers)
        entries = resp.json()
        assert len(entries) >= 1
        title_entry = next((e for e in entries if e["field"] == "title"), None)
        assert title_entry is not None
        assert title_entry["old_value"] == "Original title"
        assert title_entry["new_value"] == "Changed title"

    def test_update_priority_logs_activity(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id, priority="low")

        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col_id, "order": 0, "priority": "high",
        }, headers=auth_headers)

        entries = client.get(f"/api/cards/{card['id']}/activity", headers=auth_headers).json()
        prio_entry = next((e for e in entries if e["field"] == "priority"), None)
        assert prio_entry is not None
        assert prio_entry["new_value"] == "high"

    def test_update_due_date_logs_activity(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id)

        due = "2030-06-15"
        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col_id, "order": 0, "due_date": due,
        }, headers=auth_headers)

        entries = client.get(f"/api/cards/{card['id']}/activity", headers=auth_headers).json()
        entry = next((e for e in entries if e["field"] == "due_date"), None)
        assert entry is not None
        assert entry["new_value"] == due

    def test_column_move_logs_activity(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        board = get_board(client, auth_headers, board_id)
        # Need at least 2 columns
        if len(board["columns"]) < 2:
            client.post("/api/columns", json={"title": "Col2", "board_id": board_id}, headers=auth_headers)
            board = get_board(client, auth_headers, board_id)
        col2_id = board["columns"][1]["id"]

        card = create_card(client, auth_headers, col_id)

        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col2_id, "order": 0,
        }, headers=auth_headers)

        entries = client.get(f"/api/cards/{card['id']}/activity", headers=auth_headers).json()
        col_entry = next((e for e in entries if e["field"] == "column"), None)
        assert col_entry is not None
        assert col_entry["old_value"] is not None
        assert col_entry["new_value"] is not None

    def test_no_change_no_activity(self, client, seeded_board, auth_headers):
        """Updating with the same value should not log activity."""
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id, "Stable card", priority="medium")

        # Update with same values
        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col_id, "order": 0,
            "title": "Stable card",
            "priority": "medium",
        }, headers=auth_headers)

        entries = client.get(f"/api/cards/{card['id']}/activity", headers=auth_headers).json()
        assert len(entries) == 0

    def test_activity_requires_auth(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id)
        resp = client.get(f"/api/cards/{card['id']}/activity")
        assert resp.status_code == 401

    def test_activity_limit_param(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id, "Multi-change card")

        # Log several changes
        for i in range(5):
            client.put(f"/api/cards/{card['id']}", json={
                "column_id": col_id, "order": 0, "priority": "high" if i % 2 == 0 else "low",
            }, headers=auth_headers)

        all_entries = client.get(f"/api/cards/{card['id']}/activity", headers=auth_headers).json()
        limited = client.get(f"/api/cards/{card['id']}/activity?limit=2", headers=auth_headers).json()
        assert len(limited) == 2
        assert len(all_entries) >= 5

    def test_activity_username_returned(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id, "User card")

        client.put(f"/api/cards/{card['id']}", json={
            "column_id": col_id, "order": 0, "priority": "high",
        }, headers=auth_headers)

        entries = client.get(f"/api/cards/{card['id']}/activity", headers=auth_headers).json()
        assert len(entries) >= 1
        assert entries[0]["username"] is not None
        assert len(entries[0]["username"]) > 0


# ══════════════════════════════════════════════════════════════════════════════
# Notifications
# ══════════════════════════════════════════════════════════════════════════════

class TestNotifications:
    def _get_notifs(self, client, headers):
        resp = client.get("/api/notifications/due", headers=headers)
        assert resp.status_code == 200
        return resp.json()

    def test_no_notifications_no_due_dates(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        create_card(client, auth_headers, col_id, "No due date card")
        notifs = self._get_notifs(client, auth_headers)
        # Our new card has no due date, so notifications should not include it
        assert all(n["card_title"] != "No due date card" for n in notifs)

    def test_overdue_card_appears(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        card = create_card(client, auth_headers, col_id, "Overdue card", due_date=yesterday)

        notifs = self._get_notifs(client, auth_headers)
        overdue = [n for n in notifs if n["card_id"] == card["id"]]
        assert len(overdue) == 1
        assert overdue[0]["type"] == "overdue"

    def test_due_soon_card_appears(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        in_two = (date.today() + timedelta(days=2)).isoformat()
        card = create_card(client, auth_headers, col_id, "Due soon card", due_date=in_two)

        notifs = self._get_notifs(client, auth_headers)
        soon = [n for n in notifs if n["card_id"] == card["id"]]
        assert len(soon) == 1
        assert soon[0]["type"] == "due_soon"

    def test_future_card_not_included(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        future = (date.today() + timedelta(days=10)).isoformat()
        card = create_card(client, auth_headers, col_id, "Far future card", due_date=future)

        notifs = self._get_notifs(client, auth_headers)
        future_items = [n for n in notifs if n["card_id"] == card["id"]]
        assert len(future_items) == 0

    def test_archived_card_not_included(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        card = create_card(client, auth_headers, col_id, "Archived overdue", due_date=yesterday)

        # Archive it
        client.put(f"/api/cards/{card['id']}/archive", headers=auth_headers)

        notifs = self._get_notifs(client, auth_headers)
        assert all(n["card_id"] != card["id"] for n in notifs)

    def test_shared_board_cards_included(self, client, seeded_board, auth_headers):
        """User2 shares board with user1; user1 sees user2's overdue cards."""
        board_id, col_id = seeded_board
        headers2 = make_user(client, "notif2")

        # Register user2 and get their username
        me2 = client.get("/api/auth/me", headers=headers2).json()
        username2 = me2["username"]

        # user1 invites user2 to their board
        client.post(f"/api/boards/{board_id}/members", json={"username": username2}, headers=auth_headers)

        # user2 creates an overdue card on user1's board
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        card = create_card(client, headers2, col_id, "User2 overdue card", due_date=yesterday)

        # user1 should see it in notifications
        notifs = self._get_notifs(client, auth_headers)
        found = [n for n in notifs if n["card_id"] == card["id"]]
        assert len(found) == 1

    def test_notifications_requires_auth(self, client):
        resp = client.get("/api/notifications/due")
        assert resp.status_code == 401

    def test_notification_has_correct_fields(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        card = create_card(client, auth_headers, col_id, "Fields check card", due_date=yesterday)

        notifs = self._get_notifs(client, auth_headers)
        n = next((x for x in notifs if x["card_id"] == card["id"]), None)
        assert n is not None
        assert "card_title" in n
        assert "board_id" in n
        assert "board_title" in n
        assert "column_title" in n
        assert "due_date" in n
        assert n["type"] in ("overdue", "due_soon")


# ══════════════════════════════════════════════════════════════════════════════
# Bulk Operations
# ══════════════════════════════════════════════════════════════════════════════

class TestBulkArchive:
    def test_bulk_archive_multiple_cards(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        c1 = create_card(client, auth_headers, col_id, "Bulk 1")
        c2 = create_card(client, auth_headers, col_id, "Bulk 2")

        resp = client.post("/api/cards/bulk/archive", json={"card_ids": [c1["id"], c2["id"]]}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["archived"] == 2

        board = get_board(client, auth_headers, board_id)
        all_ids = [cid for col in board["columns"] for cid in col["cardIds"]]
        assert c1["id"] not in all_ids
        assert c2["id"] not in all_ids

    def test_bulk_archive_empty_list(self, client, auth_headers):
        resp = client.post("/api/cards/bulk/archive", json={"card_ids": []}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["archived"] == 0

    def test_bulk_archive_cross_user_rejected(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id, "Private card")

        # Other user cannot archive
        headers2 = make_user(client, "bulk_x")
        resp = client.post("/api/cards/bulk/archive", json={"card_ids": [card["id"]]}, headers=headers2)
        assert resp.status_code == 404

    def test_bulk_archive_requires_auth(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id)
        resp = client.post("/api/cards/bulk/archive", json={"card_ids": [card["id"]]})
        assert resp.status_code == 401

    def test_bulk_archive_mixed_access_fails_atomically(self, client, seeded_board, auth_headers):
        """If any card is inaccessible, none should be archived."""
        board_id, col_id = seeded_board
        valid_card = create_card(client, auth_headers, col_id, "Valid card")
        fake_id = "card-doesnotexist"

        resp = client.post(
            "/api/cards/bulk/archive",
            json={"card_ids": [valid_card["id"], fake_id]},
            headers=auth_headers,
        )
        assert resp.status_code == 404

        # Valid card should NOT be archived
        board = get_board(client, auth_headers, board_id)
        all_ids = [cid for col in board["columns"] for cid in col["cardIds"]]
        assert valid_card["id"] in all_ids


class TestBulkUpdate:
    def test_bulk_update_move_to_column(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        # Ensure we have a second column
        r = client.post("/api/columns", json={"title": "Bulk Dest", "board_id": board_id}, headers=auth_headers)
        col2_id = r.json()["id"]

        c1 = create_card(client, auth_headers, col_id, "Move me 1")
        c2 = create_card(client, auth_headers, col_id, "Move me 2")

        resp = client.post("/api/cards/bulk/update", json={
            "card_ids": [c1["id"], c2["id"]], "column_id": col2_id
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["updated"] == 2

        board = get_board(client, auth_headers, board_id)
        col2 = next(c for c in board["columns"] if c["id"] == col2_id)
        assert c1["id"] in col2["cardIds"]
        assert c2["id"] in col2["cardIds"]

    def test_bulk_update_assign_labels(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        c1 = create_card(client, auth_headers, col_id, "Label me 1")
        c2 = create_card(client, auth_headers, col_id, "Label me 2")

        resp = client.post("/api/cards/bulk/update", json={
            "card_ids": [c1["id"], c2["id"]], "labels": "urgent,backend"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["updated"] == 2

        board = get_board(client, auth_headers, board_id)
        # Verify labels updated
        for card_id in [c1["id"], c2["id"]]:
            assert board["cards"][card_id]["labels"] == "urgent,backend"

    def test_bulk_update_empty_list(self, client, auth_headers):
        resp = client.post("/api/cards/bulk/update", json={
            "card_ids": [], "labels": "x"
        }, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["updated"] == 0

    def test_bulk_update_no_updates(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id)
        resp = client.post("/api/cards/bulk/update", json={"card_ids": [card["id"]]}, headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["updated"] == 0

    def test_bulk_update_invalid_column(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id)
        resp = client.post("/api/cards/bulk/update", json={
            "card_ids": [card["id"]], "column_id": "col-doesnotexist"
        }, headers=auth_headers)
        assert resp.status_code == 404

    def test_bulk_update_cross_user_rejected(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id)

        headers2 = make_user(client, "bulk_u2")
        resp = client.post("/api/cards/bulk/update", json={
            "card_ids": [card["id"]], "labels": "hacked"
        }, headers=headers2)
        assert resp.status_code == 404

    def test_bulk_update_requires_auth(self, client, seeded_board, auth_headers):
        board_id, col_id = seeded_board
        card = create_card(client, auth_headers, col_id)
        resp = client.post("/api/cards/bulk/update", json={"card_ids": [card["id"]], "labels": "x"})
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# Board Templates
# ══════════════════════════════════════════════════════════════════════════════

class TestBoardTemplates:
    def _create_board(self, client, headers, title, template=None):
        body = {"title": title}
        if template:
            body["template"] = template
        resp = client.post("/api/boards", json=body, headers=headers)
        assert resp.status_code == 201
        return resp.json()

    def _get_columns(self, client, headers, board_id):
        data = client.get(f"/api/boards/{board_id}", headers=headers).json()
        return data["columns"]

    def test_no_template_gives_3_default_columns(self, client, auth_headers):
        board = self._create_board(client, auth_headers, "Default Board")
        cols = self._get_columns(client, auth_headers, board["id"])
        assert len(cols) == 3
        titles = [c["title"] for c in cols]
        assert "Backlog" in titles
        assert "In Progress" in titles
        assert "Done" in titles

    def test_software_template_gives_5_columns(self, client, auth_headers):
        board = self._create_board(client, auth_headers, "SW Board", template="software")
        cols = self._get_columns(client, auth_headers, board["id"])
        assert len(cols) == 5
        titles = [c["title"] for c in cols]
        assert "Backlog" in titles
        assert "In Progress" in titles
        assert "In Review" in titles
        assert "Testing" in titles
        assert "Done" in titles

    def test_software_template_wip_limits(self, client, auth_headers):
        board = self._create_board(client, auth_headers, "SW WIP Board", template="software")
        cols = self._get_columns(client, auth_headers, board["id"])
        in_progress = next(c for c in cols if c["title"] == "In Progress")
        in_review = next(c for c in cols if c["title"] == "In Review")
        assert in_progress["wip_limit"] == 3
        assert in_review["wip_limit"] == 2

    def test_marketing_template_gives_5_columns(self, client, auth_headers):
        board = self._create_board(client, auth_headers, "MKT Board", template="marketing")
        cols = self._get_columns(client, auth_headers, board["id"])
        assert len(cols) == 5
        titles = [c["title"] for c in cols]
        assert "Ideas" in titles
        assert "Planning" in titles
        assert "In Production" in titles
        assert "Review" in titles
        assert "Published" in titles

    def test_personal_template_gives_3_columns(self, client, auth_headers):
        board = self._create_board(client, auth_headers, "Personal Board", template="personal")
        cols = self._get_columns(client, auth_headers, board["id"])
        assert len(cols) == 3
        titles = [c["title"] for c in cols]
        assert "To Do" in titles
        assert "Doing" in titles
        assert "Done" in titles

    def test_personal_template_wip_limit(self, client, auth_headers):
        board = self._create_board(client, auth_headers, "Personal WIP", template="personal")
        cols = self._get_columns(client, auth_headers, board["id"])
        doing = next(c for c in cols if c["title"] == "Doing")
        assert doing["wip_limit"] == 3

    def test_unknown_template_falls_back_to_default(self, client, auth_headers):
        board = self._create_board(client, auth_headers, "Unknown Template Board", template="nonexistent")
        cols = self._get_columns(client, auth_headers, board["id"])
        assert len(cols) == 3  # default 3 columns

    def test_marketing_template_wip_limit(self, client, auth_headers):
        board = self._create_board(client, auth_headers, "MKT WIP", template="marketing")
        cols = self._get_columns(client, auth_headers, board["id"])
        in_prod = next(c for c in cols if c["title"] == "In Production")
        assert in_prod["wip_limit"] == 2
