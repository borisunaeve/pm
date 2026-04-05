"""Tests for board CRUD endpoints."""
import uuid


class TestListBoards:
    def test_list_boards_returns_list(self, client, auth_headers):
        resp = client.get("/api/boards", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_list_boards_unauthenticated(self, client):
        resp = client.get("/api/boards")
        assert resp.status_code in (401, 403)

    def test_boards_isolated_between_users(self, client):
        """Two users should not see each other's boards."""
        def make_headers(suffix):
            uname = f"isolated_{suffix}_{uuid.uuid4().hex[:6]}"
            r = client.post("/api/auth/register", json={"username": uname, "password": "pass123456"})
            return {"Authorization": f"Bearer {r.json()['access_token']}"}

        h1, h2 = make_headers("a"), make_headers("b")

        # Each user auto-gets a board on register; create another for user1
        client.post("/api/boards", json={"title": "User1 Extra Board"}, headers=h1)

        u1_boards = client.get("/api/boards", headers=h1).json()
        u2_boards = client.get("/api/boards", headers=h2).json()

        u1_ids = {b["id"] for b in u1_boards}
        u2_ids = {b["id"] for b in u2_boards}
        assert u1_ids.isdisjoint(u2_ids)


class TestCreateBoard:
    def test_create_board(self, client, auth_headers):
        resp = client.post("/api/boards", json={"title": "New Project"}, headers=auth_headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Project"
        assert "id" in data

    def test_create_board_has_default_columns(self, client, auth_headers):
        resp = client.post("/api/boards", json={"title": "Board with cols"}, headers=auth_headers)
        board_id = resp.json()["id"]
        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        assert len(board["columns"]) == 3

    def test_create_board_empty_title(self, client, auth_headers):
        resp = client.post("/api/boards", json={"title": "   "}, headers=auth_headers)
        assert resp.status_code == 400


class TestGetBoard:
    def test_get_board(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        resp = client.get(f"/api/boards/{board_id}", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "columns" in data
        assert "cards" in data

    def test_get_board_wrong_user(self, client):
        # Register user A, create a board
        uname_a = f"ua_{uuid.uuid4().hex[:6]}"
        r = client.post("/api/auth/register", json={"username": uname_a, "password": "pass123456"})
        ha = {"Authorization": f"Bearer {r.json()['access_token']}"}
        board_id = client.get("/api/boards", headers=ha).json()[0]["id"]

        # Register user B and try to access A's board
        uname_b = f"ub_{uuid.uuid4().hex[:6]}"
        r2 = client.post("/api/auth/register", json={"username": uname_b, "password": "pass123456"})
        hb = {"Authorization": f"Bearer {r2.json()['access_token']}"}

        resp = client.get(f"/api/boards/{board_id}", headers=hb)
        assert resp.status_code == 404


class TestUpdateBoard:
    def test_update_board_title(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        resp = client.put(f"/api/boards/{board_id}", json={"title": "Renamed Board"}, headers=auth_headers)
        assert resp.status_code == 200

        # Verify change
        boards = client.get("/api/boards", headers=auth_headers).json()
        titles = {b["title"] for b in boards}
        assert "Renamed Board" in titles

    def test_update_board_not_found(self, client, auth_headers):
        resp = client.put("/api/boards/nonexistent", json={"title": "X"}, headers=auth_headers)
        assert resp.status_code == 404


class TestDeleteBoard:
    def test_delete_board(self, client, auth_headers):
        resp = client.post("/api/boards", json={"title": "To Delete"}, headers=auth_headers)
        board_id = resp.json()["id"]

        del_resp = client.delete(f"/api/boards/{board_id}", headers=auth_headers)
        assert del_resp.status_code == 204

        boards = client.get("/api/boards", headers=auth_headers).json()
        assert not any(b["id"] == board_id for b in boards)

    def test_delete_board_not_owned(self, client):
        uname = f"del_{uuid.uuid4().hex[:6]}"
        r = client.post("/api/auth/register", json={"username": uname, "password": "pass123456"})
        ha = {"Authorization": f"Bearer {r.json()['access_token']}"}
        board_id = client.get("/api/boards", headers=ha).json()[0]["id"]

        uname2 = f"del2_{uuid.uuid4().hex[:6]}"
        r2 = client.post("/api/auth/register", json={"username": uname2, "password": "pass123456"})
        hb = {"Authorization": f"Bearer {r2.json()['access_token']}"}

        resp = client.delete(f"/api/boards/{board_id}", headers=hb)
        assert resp.status_code == 404
