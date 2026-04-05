"""Tests for column CRUD endpoints."""
import uuid


class TestCreateColumn:
    def test_create_column(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        resp = client.post(
            "/api/columns",
            json={"title": "New Column", "board_id": board_id},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "New Column"
        assert "id" in data

    def test_create_column_appended_to_board(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        before = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        count_before = len(before["columns"])

        client.post(
            "/api/columns",
            json={"title": "Extra", "board_id": board_id},
            headers=auth_headers,
        )

        after = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        assert len(after["columns"]) == count_before + 1

    def test_create_column_empty_title(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        resp = client.post(
            "/api/columns",
            json={"title": "", "board_id": board_id},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_create_column_wrong_board(self, client, auth_headers):
        resp = client.post(
            "/api/columns",
            json={"title": "X", "board_id": "nonexistent-board"},
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestUpdateColumn:
    def test_rename_column(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        resp = client.put(
            f"/api/columns/{col_id}",
            json={"title": "Renamed Col"},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        col = next(c for c in board["columns"] if c["id"] == col_id)
        assert col["title"] == "Renamed Col"

    def test_rename_column_not_owned(self, client, seeded_board):
        _, col_id = seeded_board
        uname = f"other_{uuid.uuid4().hex[:6]}"
        r = client.post("/api/auth/register", json={"username": uname, "password": "pass123456"})
        h2 = {"Authorization": f"Bearer {r.json()['access_token']}"}

        resp = client.put(f"/api/columns/{col_id}", json={"title": "Hack"}, headers=h2)
        assert resp.status_code == 404


class TestDeleteColumn:
    def test_delete_column(self, client, auth_headers, seeded_board):
        board_id, _ = seeded_board
        # Create a new column to delete
        col_resp = client.post(
            "/api/columns",
            json={"title": "Temp Column", "board_id": board_id},
            headers=auth_headers,
        )
        col_id = col_resp.json()["id"]

        del_resp = client.delete(f"/api/columns/{col_id}", headers=auth_headers)
        assert del_resp.status_code == 204

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        assert not any(c["id"] == col_id for c in board["columns"])

    def test_delete_column_not_found(self, client, auth_headers):
        resp = client.delete("/api/columns/nonexistent", headers=auth_headers)
        assert resp.status_code == 404
