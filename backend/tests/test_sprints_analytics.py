"""Tests for sprints and analytics endpoints."""
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_card(client, auth_headers, col_id, title="Card", **kwargs):
    resp = client.post(
        "/api/cards",
        json={"title": title, "column_id": col_id, **kwargs},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


def _make_sprint(client, auth_headers, board_id, title="Sprint 1", **kwargs):
    resp = client.post(
        f"/api/boards/{board_id}/sprints",
        json={"title": title, **kwargs},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


# ══════════════════════════════════════════════════════════════════════════════
# Sprint CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestCreateSprint:
    def test_create_sprint_minimal(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id)
        assert sprint["id"].startswith("sprint-")
        assert sprint["title"] == "Sprint 1"
        assert sprint["status"] == "planning"
        assert sprint["board_id"] == board_id
        assert sprint["card_count"] == 0

    def test_create_sprint_with_all_fields(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        sprint = _make_sprint(
            client, auth_headers, board_id,
            title="Sprint 2",
            goal="Ship login feature",
            start_date="2026-04-01",
            end_date="2026-04-14",
        )
        assert sprint["goal"] == "Ship login feature"
        assert sprint["start_date"] == "2026-04-01"
        assert sprint["end_date"] == "2026-04-14"

    def test_create_sprint_empty_title_rejected(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        resp = client.post(
            f"/api/boards/{board_id}/sprints",
            json={"title": "  "},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_create_sprint_requires_auth(self, client, seeded_board):
        board_id, _ = seeded_board
        resp = client.post(f"/api/boards/{board_id}/sprints", json={"title": "S"})
        assert resp.status_code == 401

    def test_create_sprint_wrong_board_rejected(self, client, auth_headers):
        resp = client.post(
            "/api/boards/board-does-not-exist/sprints",
            json={"title": "Bad"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestListSprints:
    def test_list_sprints_empty(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        resp = client.get(f"/api/boards/{board_id}/sprints", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_sprints_returns_created(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        _make_sprint(client, auth_headers, board_id, title="A")
        _make_sprint(client, auth_headers, board_id, title="B")
        resp = client.get(f"/api/boards/{board_id}/sprints", headers=auth_headers)
        titles = [s["title"] for s in resp.json()]
        assert "A" in titles
        assert "B" in titles

    def test_list_sprints_includes_card_count(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id, title="Count Sprint")
        _make_card(client, auth_headers, col_id, title="C1", sprint_id=sprint["id"])
        _make_card(client, auth_headers, col_id, title="C2", sprint_id=sprint["id"])

        sprints = client.get(f"/api/boards/{board_id}/sprints", headers=auth_headers).json()
        found = next(s for s in sprints if s["id"] == sprint["id"])
        assert found["card_count"] == 2


class TestGetSprint:
    def test_get_sprint(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id)
        resp = client.get(f"/api/sprints/{sprint['id']}", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == sprint["id"]

    def test_get_nonexistent_sprint(self, client, auth_headers):
        resp = client.get("/api/sprints/sprint-doesnotexist", headers=auth_headers)
        assert resp.status_code == 404


class TestUpdateSprint:
    def test_update_sprint_title(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id, title="Old Title")
        resp = client.put(
            f"/api/sprints/{sprint['id']}",
            json={"title": "New Title", "goal": "New Goal"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["title"] == "New Title"
        assert resp.json()["goal"] == "New Goal"

    def test_update_sprint_empty_title_rejected(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id)
        resp = client.put(
            f"/api/sprints/{sprint['id']}",
            json={"title": ""},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_update_sprint_dates(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id)
        resp = client.put(
            f"/api/sprints/{sprint['id']}",
            json={"start_date": "2026-05-01", "end_date": "2026-05-14"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["start_date"] == "2026-05-01"
        assert data["end_date"] == "2026-05-14"


class TestDeleteSprint:
    def test_delete_sprint(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id)
        resp = client.delete(f"/api/sprints/{sprint['id']}", headers=auth_headers)
        assert resp.status_code == 204

        get_resp = client.get(f"/api/sprints/{sprint['id']}", headers=auth_headers)
        assert get_resp.status_code == 404

    def test_delete_sprint_unlinks_cards(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id, title="To Delete")
        card = _make_card(client, auth_headers, col_id, title="Linked Card", sprint_id=sprint["id"])

        client.delete(f"/api/sprints/{sprint['id']}", headers=auth_headers)

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        assert board["cards"][card["id"]]["sprint_id"] is None


# ══════════════════════════════════════════════════════════════════════════════
# Sprint Lifecycle (start / complete)
# ══════════════════════════════════════════════════════════════════════════════

class TestSprintLifecycle:
    def test_start_sprint(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id)
        resp = client.post(f"/api/sprints/{sprint['id']}/start", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_only_one_active_sprint_per_board(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        s1 = _make_sprint(client, auth_headers, board_id, title="S1")
        s2 = _make_sprint(client, auth_headers, board_id, title="S2")
        client.post(f"/api/sprints/{s1['id']}/start", headers=auth_headers)
        resp = client.post(f"/api/sprints/{s2['id']}/start", headers=auth_headers)
        assert resp.status_code == 409

    def test_cannot_start_already_active_sprint(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id)
        client.post(f"/api/sprints/{sprint['id']}/start", headers=auth_headers)
        resp = client.post(f"/api/sprints/{sprint['id']}/start", headers=auth_headers)
        assert resp.status_code == 400

    def test_complete_sprint(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id)
        client.post(f"/api/sprints/{sprint['id']}/start", headers=auth_headers)
        resp = client.post(f"/api/sprints/{sprint['id']}/complete", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_cannot_complete_planning_sprint(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id)
        resp = client.post(f"/api/sprints/{sprint['id']}/complete", headers=auth_headers)
        assert resp.status_code == 400

    def test_after_completing_can_start_new_sprint(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        s1 = _make_sprint(client, auth_headers, board_id, title="S1")
        s2 = _make_sprint(client, auth_headers, board_id, title="S2")
        client.post(f"/api/sprints/{s1['id']}/start", headers=auth_headers)
        client.post(f"/api/sprints/{s1['id']}/complete", headers=auth_headers)
        resp = client.post(f"/api/sprints/{s2['id']}/start", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"


# ══════════════════════════════════════════════════════════════════════════════
# Card sprint_id field
# ══════════════════════════════════════════════════════════════════════════════

class TestCardSprintAssignment:
    def test_create_card_with_sprint(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id)
        card = _make_card(client, auth_headers, col_id, title="Sprinted", sprint_id=sprint["id"])
        assert card["sprint_id"] == sprint["id"]

    def test_sprint_appears_on_board(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id, title="My Sprint")
        card = _make_card(client, auth_headers, col_id, title="Sprint Card", sprint_id=sprint["id"])

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        board_card = board["cards"][card["id"]]
        assert board_card["sprint_id"] == sprint["id"]
        assert board_card["sprint_title"] == "My Sprint"

    def test_update_card_sprint_id(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id)
        card = _make_card(client, auth_headers, col_id, title="No Sprint Card")

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        col = next(c for c in board["columns"] if c["id"] == col_id)
        order = col["cardIds"].index(card["id"])

        resp = client.put(
            f"/api/cards/{card['id']}",
            json={"column_id": col_id, "order": order, "sprint_id": sprint["id"]},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        assert board["cards"][card["id"]]["sprint_id"] == sprint["id"]

    def test_sprint_card_count_updates(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id)
        _make_card(client, auth_headers, col_id, sprint_id=sprint["id"])
        _make_card(client, auth_headers, col_id, sprint_id=sprint["id"])
        _make_card(client, auth_headers, col_id)  # no sprint

        sp = client.get(f"/api/sprints/{sprint['id']}", headers=auth_headers).json()
        assert sp["card_count"] == 2


# ══════════════════════════════════════════════════════════════════════════════
# Board Analytics
# ══════════════════════════════════════════════════════════════════════════════

class TestBoardAnalytics:
    def test_analytics_returns_correct_shape(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        resp = client.get(f"/api/boards/{board_id}/analytics", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_cards" in data
        assert "archived_cards" in data
        assert "overdue_cards" in data
        assert "due_this_week" in data
        assert "by_column" in data
        assert "by_priority" in data
        assert "by_label" in data
        assert "sprints" in data
        assert "avg_estimated_hours" in data
        assert "avg_actual_hours" in data

    def test_analytics_total_cards(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        resp_before = client.get(f"/api/boards/{board_id}/analytics", headers=auth_headers).json()
        initial = resp_before["total_cards"]

        _make_card(client, auth_headers, col_id, title="Analytics Card 1")
        _make_card(client, auth_headers, col_id, title="Analytics Card 2")

        resp_after = client.get(f"/api/boards/{board_id}/analytics", headers=auth_headers).json()
        assert resp_after["total_cards"] == initial + 2

    def test_analytics_archived_cards(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        card = _make_card(client, auth_headers, col_id, title="To Archive Analytics")
        client.put(f"/api/cards/{card['id']}/archive", headers=auth_headers)

        data = client.get(f"/api/boards/{board_id}/analytics", headers=auth_headers).json()
        assert data["archived_cards"] >= 1

    def test_analytics_overdue_cards(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        _make_card(
            client, auth_headers, col_id,
            title="Overdue Card",
            due_date="2020-01-01",
        )
        data = client.get(f"/api/boards/{board_id}/analytics", headers=auth_headers).json()
        assert data["overdue_cards"] >= 1

    def test_analytics_by_column(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        data = client.get(f"/api/boards/{board_id}/analytics", headers=auth_headers).json()
        assert len(data["by_column"]) > 0
        col_entry = next((c for c in data["by_column"] if c["column_id"] == col_id), None)
        assert col_entry is not None
        assert "total" in col_entry

    def test_analytics_by_priority(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        _make_card(client, auth_headers, col_id, title="High P", priority="high")
        data = client.get(f"/api/boards/{board_id}/analytics", headers=auth_headers).json()
        priorities = [p["priority"] for p in data["by_priority"]]
        assert "high" in priorities

    def test_analytics_by_label(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        _make_card(client, auth_headers, col_id, title="Labeled", labels="frontend,bug")
        data = client.get(f"/api/boards/{board_id}/analytics", headers=auth_headers).json()
        labels = [l["label"] for l in data["by_label"]]
        assert "frontend" in labels
        assert "bug" in labels

    def test_analytics_sprint_progress(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        sprint = _make_sprint(client, auth_headers, board_id, title="Analytics Sprint")
        _make_card(client, auth_headers, col_id, sprint_id=sprint["id"], estimated_hours=8.0)
        _make_card(client, auth_headers, col_id, sprint_id=sprint["id"], estimated_hours=4.0)

        data = client.get(f"/api/boards/{board_id}/analytics", headers=auth_headers).json()
        sprint_data = next((s for s in data["sprints"] if s["sprint_id"] == sprint["id"]), None)
        assert sprint_data is not None
        assert sprint_data["total_cards"] == 2
        assert sprint_data["estimated_hours"] == 12.0

    def test_analytics_avg_time_tracking(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        _make_card(client, auth_headers, col_id, title="Timed 1", estimated_hours=10.0, actual_hours=8.0)
        _make_card(client, auth_headers, col_id, title="Timed 2", estimated_hours=6.0, actual_hours=4.0)
        data = client.get(f"/api/boards/{board_id}/analytics", headers=auth_headers).json()
        assert data["avg_estimated_hours"] > 0

    def test_analytics_requires_auth(self, client, seeded_board):
        board_id, _ = seeded_board
        resp = client.get(f"/api/boards/{board_id}/analytics")
        assert resp.status_code == 401

    def test_analytics_wrong_board_rejected(self, client, auth_headers):
        resp = client.get("/api/boards/board-does-not-exist/analytics", headers=auth_headers)
        assert resp.status_code == 404

    def test_analytics_isolated_between_users(self, client, seeded_board):
        import uuid
        other = f"other_{uuid.uuid4().hex[:6]}"
        r = client.post("/api/auth/register", json={"username": other, "password": "pass123"})
        other_headers = {"Authorization": f"Bearer {r.json()['access_token']}"}
        board_id, _ = seeded_board
        resp = client.get(f"/api/boards/{board_id}/analytics", headers=other_headers)
        assert resp.status_code == 404
