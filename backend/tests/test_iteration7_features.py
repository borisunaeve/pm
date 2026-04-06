"""
Tests for iteration 7 features:
  - Card color field (set/update/read via board data)
  - Time tracking fields on cards (estimated_hours, actual_hours)
  - Board templates API (GET /api/templates)
"""
import uuid
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_user(client, prefix="u7"):
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
# Card Color
# ══════════════════════════════════════════════════════════════════════════════

class TestCardColor:
    def test_create_card_with_color(self, client):
        h, uid, uname = make_user(client, "cc1")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "Colored card", color="#ff5733")
        assert card["color"] == "#ff5733"

    def test_create_card_color_defaults_null(self, client):
        h, uid, uname = make_user(client, "cc2")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "No color card")
        assert card["color"] is None

    def test_update_card_color(self, client):
        h, uid, uname = make_user(client, "cc3")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "Card to color")
        resp = client.put(
            f"/api/cards/{card['id']}",
            json={"column_id": col_id, "order": 0, "color": "#00aaff"},
            headers=h,
        )
        assert resp.status_code == 200

    def test_card_color_appears_in_board_data(self, client):
        h, uid, uname = make_user(client, "cc4")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "Board color test", color="#abc123")
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        assert board["cards"][card["id"]]["color"] == "#abc123"

    def test_update_color_reflected_in_board(self, client):
        h, uid, uname = make_user(client, "cc5")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "Update color test")
        client.put(
            f"/api/cards/{card['id']}",
            json={"column_id": col_id, "order": 0, "color": "#112233"},
            headers=h,
        )
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        assert board["cards"][card["id"]]["color"] == "#112233"

    def test_clear_card_color(self, client):
        h, uid, uname = make_user(client, "cc6")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "Clear color", color="#ff0000")
        client.put(
            f"/api/cards/{card['id']}",
            json={"column_id": col_id, "order": 0, "color": ""},
            headers=h,
        )
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        assert board["cards"][card["id"]]["color"] is None

    def test_multiple_cards_different_colors(self, client):
        h, uid, uname = make_user(client, "cc7")
        board_id, col_id = get_board_and_col(client, h)
        c1 = create_card(client, h, col_id, "Red card", color="#ff0000")
        c2 = create_card(client, h, col_id, "Blue card", color="#0000ff")
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        assert board["cards"][c1["id"]]["color"] == "#ff0000"
        assert board["cards"][c2["id"]]["color"] == "#0000ff"

    def test_color_auth_required(self, client):
        h, uid, uname = make_user(client, "cc8")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "Auth color")
        resp = client.put(
            f"/api/cards/{card['id']}",
            json={"column_id": col_id, "order": 0, "color": "#ff0000"},
        )
        assert resp.status_code == 401


# ══════════════════════════════════════════════════════════════════════════════
# Time Tracking
# ══════════════════════════════════════════════════════════════════════════════

class TestTimeTracking:
    def test_create_card_with_time_estimate(self, client):
        h, uid, uname = make_user(client, "tt1")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "Timed card", estimated_hours=4.0)
        assert card["estimated_hours"] == 4.0

    def test_create_card_with_actual_hours(self, client):
        h, uid, uname = make_user(client, "tt2")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "Actual hours", estimated_hours=3.0, actual_hours=2.5)
        assert card["estimated_hours"] == 3.0
        assert card["actual_hours"] == 2.5

    def test_time_tracking_in_board_data(self, client):
        h, uid, uname = make_user(client, "tt3")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "Board time", estimated_hours=8.0, actual_hours=6.0)
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        c = board["cards"][card["id"]]
        assert c["estimated_hours"] == 8.0
        assert c["actual_hours"] == 6.0

    def test_update_estimated_hours(self, client):
        h, uid, uname = make_user(client, "tt4")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "Update estimate")
        client.put(
            f"/api/cards/{card['id']}",
            json={"column_id": col_id, "order": 0, "estimated_hours": 5.0},
            headers=h,
        )
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        assert board["cards"][card["id"]]["estimated_hours"] == 5.0

    def test_update_actual_hours(self, client):
        h, uid, uname = make_user(client, "tt5")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "Log time", estimated_hours=4.0)
        client.put(
            f"/api/cards/{card['id']}",
            json={"column_id": col_id, "order": 0, "actual_hours": 3.5},
            headers=h,
        )
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        assert board["cards"][card["id"]]["actual_hours"] == 3.5

    def test_fractional_hours_stored(self, client):
        h, uid, uname = make_user(client, "tt6")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "Fractional", estimated_hours=1.25)
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        assert board["cards"][card["id"]]["estimated_hours"] == 1.25

    def test_time_defaults_null(self, client):
        h, uid, uname = make_user(client, "tt7")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "No time")
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        c = board["cards"][card["id"]]
        assert c["estimated_hours"] is None
        assert c["actual_hours"] is None

    def test_analytics_includes_hours(self, client):
        h, uid, uname = make_user(client, "tt8")
        board_id, col_id = get_board_and_col(client, h)
        create_card(client, h, col_id, "A1", estimated_hours=4.0, actual_hours=3.0)
        create_card(client, h, col_id, "A2", estimated_hours=2.0, actual_hours=2.0)
        analytics = client.get(f"/api/boards/{board_id}/analytics", headers=h).json()
        assert analytics["avg_estimated_hours"] > 0
        assert analytics["avg_actual_hours"] > 0


# ══════════════════════════════════════════════════════════════════════════════
# Board Templates
# ══════════════════════════════════════════════════════════════════════════════

class TestBoardTemplates:
    def test_list_templates_requires_auth(self, client):
        resp = client.get("/api/templates")
        assert resp.status_code == 401

    def test_list_templates_returns_list(self, client):
        h, uid, uname = make_user(client, "bt1")
        resp = client.get("/api/templates", headers=h)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 3

    def test_templates_have_required_fields(self, client):
        h, uid, uname = make_user(client, "bt2")
        templates = client.get("/api/templates", headers=h).json()
        for t in templates:
            assert "id" in t
            assert "name" in t
            assert "description" in t
            assert "columns" in t
            assert isinstance(t["columns"], list)
            assert len(t["columns"]) > 0

    def test_software_template_exists(self, client):
        h, uid, uname = make_user(client, "bt3")
        templates = client.get("/api/templates", headers=h).json()
        ids = [t["id"] for t in templates]
        assert "software" in ids

    def test_marketing_template_exists(self, client):
        h, uid, uname = make_user(client, "bt4")
        templates = client.get("/api/templates", headers=h).json()
        ids = [t["id"] for t in templates]
        assert "marketing" in ids

    def test_personal_template_exists(self, client):
        h, uid, uname = make_user(client, "bt5")
        templates = client.get("/api/templates", headers=h).json()
        ids = [t["id"] for t in templates]
        assert "personal" in ids

    def test_create_board_from_software_template(self, client):
        h, uid, uname = make_user(client, "bt6")
        resp = client.post("/api/boards", json={"title": "My Software Board", "template": "software"}, headers=h)
        assert resp.status_code == 201
        board_id = resp.json()["id"]
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        col_titles = [c["title"] for c in board["columns"]]
        assert "Backlog" in col_titles
        assert "In Progress" in col_titles
        assert "Done" in col_titles

    def test_create_board_from_marketing_template(self, client):
        h, uid, uname = make_user(client, "bt7")
        resp = client.post("/api/boards", json={"title": "Campaign", "template": "marketing"}, headers=h)
        assert resp.status_code == 201
        board_id = resp.json()["id"]
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        col_titles = [c["title"] for c in board["columns"]]
        assert "Ideas" in col_titles
        assert "Published" in col_titles

    def test_create_board_from_personal_template(self, client):
        h, uid, uname = make_user(client, "bt8")
        resp = client.post("/api/boards", json={"title": "Personal", "template": "personal"}, headers=h)
        assert resp.status_code == 201
        board_id = resp.json()["id"]
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        col_titles = [c["title"] for c in board["columns"]]
        assert "To Do" in col_titles
        assert "Done" in col_titles

    def test_create_board_no_template_gives_default_columns(self, client):
        h, uid, uname = make_user(client, "bt9")
        resp = client.post("/api/boards", json={"title": "Blank Board"}, headers=h)
        assert resp.status_code == 201
        board_id = resp.json()["id"]
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        assert len(board["columns"]) > 0

    def test_template_color_available(self, client):
        h, uid, uname = make_user(client, "bt10")
        templates = client.get("/api/templates", headers=h).json()
        for t in templates:
            assert "color" in t
