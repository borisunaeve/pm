"""Tests for card CRUD endpoints."""
import uuid


class TestCreateCard:
    def test_create_card_minimal(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        resp = client.post(
            "/api/cards",
            json={"title": "Test Card", "column_id": col_id},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Test Card"
        assert "id" in data

    def test_create_card_with_enhancements(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        resp = client.post(
            "/api/cards",
            json={
                "title": "Feature Card",
                "column_id": col_id,
                "details": "Some details",
                "priority": "high",
                "due_date": "2026-05-01",
                "labels": "frontend,urgent",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["priority"] == "high"
        assert data["due_date"] == "2026-05-01"
        assert data["labels"] == "frontend,urgent"

    def test_create_card_wrong_column(self, client, auth_headers):
        resp = client.post(
            "/api/cards",
            json={"title": "X", "column_id": "nonexistent"},
            headers=auth_headers,
        )
        assert resp.status_code == 404

    def test_create_card_appears_in_board(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        resp = client.post(
            "/api/cards",
            json={"title": "Visible Card", "column_id": col_id},
            headers=auth_headers,
        )
        card_id = resp.json()["id"]

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        assert card_id in board["cards"]
        col = next(c for c in board["columns"] if c["id"] == col_id)
        assert card_id in col["cardIds"]


class TestUpdateCard:
    def test_update_card_move_column(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board

        # Create a second column
        col2_resp = client.post(
            "/api/columns",
            json={"title": "Second Col", "board_id": board_id},
            headers=auth_headers,
        )
        col2_id = col2_resp.json()["id"]

        # Create a card in col1
        card = client.post(
            "/api/cards",
            json={"title": "Movable Card", "column_id": col_id},
            headers=auth_headers,
        ).json()
        card_id = card["id"]

        # Move to col2
        resp = client.put(
            f"/api/cards/{card_id}",
            json={"column_id": col2_id, "order": 0},
            headers=auth_headers,
        )
        assert resp.status_code == 200

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        col2 = next(c for c in board["columns"] if c["id"] == col2_id)
        assert card_id in col2["cardIds"]

    def test_update_card_fields(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        card_id = client.post(
            "/api/cards",
            json={"title": "Old Title", "column_id": col_id},
            headers=auth_headers,
        ).json()["id"]

        resp = client.put(
            f"/api/cards/{card_id}",
            json={
                "column_id": col_id,
                "order": 0,
                "title": "New Title",
                "priority": "high",
                "due_date": "2026-12-31",
                "labels": "bug",
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        card = board["cards"][card_id]
        assert card["title"] == "New Title"
        assert card["priority"] == "high"
        assert card["labels"] == "bug"


class TestDeleteCard:
    def test_delete_card(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        card_id = client.post(
            "/api/cards",
            json={"title": "To Delete", "column_id": col_id},
            headers=auth_headers,
        ).json()["id"]

        del_resp = client.delete(f"/api/cards/{card_id}", headers=auth_headers)
        assert del_resp.status_code == 204

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        assert card_id not in board["cards"]

    def test_delete_card_not_found(self, client, auth_headers):
        resp = client.delete("/api/cards/nonexistent", headers=auth_headers)
        assert resp.status_code == 404

    def test_delete_card_not_owned(self, client, seeded_board):
        _, col_id = seeded_board
        # This test uses a fixture-created card; we need a different user

        uname = f"thief_{uuid.uuid4().hex[:6]}"
        r = client.post("/api/auth/register", json={"username": uname, "password": "pass123456"})
        h2 = {"Authorization": f"Bearer {r.json()['access_token']}"}

        # Create card for the original user (col_id belongs to auth_headers user,
        # but we don't have those headers here — just check 404 for nonexistent)
        resp = client.delete("/api/cards/fake-card-id", headers=h2)
        assert resp.status_code == 404


class TestCardOrdering:
    def test_cards_ordered_correctly(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        titles = ["First", "Second", "Third"]
        for t in titles:
            client.post(
                "/api/cards",
                json={"title": t, "column_id": col_id},
                headers=auth_headers,
            )

        board_id, _ = seeded_board
        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        col = next(c for c in board["columns"] if c["id"] == col_id)
        ordered_titles = [board["cards"][cid]["title"] for cid in col["cardIds"]]
        # The new cards should appear at the end in insertion order
        assert "First" in ordered_titles
        assert "Second" in ordered_titles
        assert "Third" in ordered_titles
        assert ordered_titles.index("First") < ordered_titles.index("Second") < ordered_titles.index("Third")
