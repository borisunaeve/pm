"""Tests for card archive/restore, copy, relations, and global search."""
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_card(client, auth_headers, col_id, title="Test Card", **kwargs):
    resp = client.post(
        "/api/cards",
        json={"title": title, "column_id": col_id, **kwargs},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    return resp.json()


# ══════════════════════════════════════════════════════════════════════════════
# Archive / Restore
# ══════════════════════════════════════════════════════════════════════════════

class TestArchiveCard:
    def test_archive_removes_card_from_board(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        card = _make_card(client, auth_headers, col_id, title="To Archive")

        resp = client.put(f"/api/cards/{card['id']}/archive", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "archived"

        # Card should not appear in normal board fetch
        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        all_card_ids = [cid for col in board["columns"] for cid in col["cardIds"]]
        assert card["id"] not in all_card_ids

    def test_archive_card_appears_with_include_archived(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        card = _make_card(client, auth_headers, col_id, title="Archived Card")
        client.put(f"/api/cards/{card['id']}/archive", headers=auth_headers)

        board = client.get(
            f"/api/boards/{board_id}?include_archived=true", headers=auth_headers
        ).json()
        assert card["id"] in board["cards"]
        assert board["cards"][card["id"]]["archived"] is True

    def test_restore_card_reappears_in_board(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        card = _make_card(client, auth_headers, col_id, title="Restore Me")
        client.put(f"/api/cards/{card['id']}/archive", headers=auth_headers)

        resp = client.put(f"/api/cards/{card['id']}/restore", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["status"] == "restored"

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        all_card_ids = [cid for col in board["columns"] for cid in col["cardIds"]]
        assert card["id"] in all_card_ids

    def test_archive_nonexistent_card_returns_404(self, client, auth_headers):
        resp = client.put("/api/cards/card-doesnotexist/archive", headers=auth_headers)
        assert resp.status_code == 404

    def test_archive_card_requires_auth(self, client, seeded_board):
        _, col_id = seeded_board
        resp = client.put("/api/cards/card-x/archive")
        assert resp.status_code == 401

    def test_archived_card_excluded_from_board_card_count(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        # Get initial count
        boards = client.get("/api/boards", headers=auth_headers).json()
        board_summary = next(b for b in boards if b["id"] == board_id)
        initial_count = board_summary["card_count"]

        card = _make_card(client, auth_headers, col_id, title="Count Test Card")
        boards = client.get("/api/boards", headers=auth_headers).json()
        board_summary = next(b for b in boards if b["id"] == board_id)
        assert board_summary["card_count"] == initial_count + 1

        client.put(f"/api/cards/{card['id']}/archive", headers=auth_headers)
        boards = client.get("/api/boards", headers=auth_headers).json()
        board_summary = next(b for b in boards if b["id"] == board_id)
        assert board_summary["card_count"] == initial_count


# ══════════════════════════════════════════════════════════════════════════════
# Copy Card
# ══════════════════════════════════════════════════════════════════════════════

class TestCopyCard:
    def test_copy_creates_new_card_in_same_column(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        card = _make_card(
            client, auth_headers, col_id,
            title="Original",
            details="Some details",
            priority="high",
            labels="bug,urgent",
        )

        resp = client.post(f"/api/cards/{card['id']}/copy", headers=auth_headers)
        assert resp.status_code == 201
        copy = resp.json()

        assert copy["id"] != card["id"]
        assert copy["title"] == "Original (copy)"
        assert copy["details"] == "Some details"
        assert copy["priority"] == "high"
        assert copy["labels"] == "bug,urgent"
        assert copy["column_id"] == col_id

    def test_copy_appears_on_board(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        card = _make_card(client, auth_headers, col_id, title="Board Copy Test")
        copy_resp = client.post(f"/api/cards/{card['id']}/copy", headers=auth_headers)
        copy_id = copy_resp.json()["id"]

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        all_card_ids = [cid for col in board["columns"] for cid in col["cardIds"]]
        assert copy_id in all_card_ids

    def test_copy_does_not_copy_archived_flag(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        card = _make_card(client, auth_headers, col_id, title="Archived Original")
        client.put(f"/api/cards/{card['id']}/archive", headers=auth_headers)

        resp = client.post(f"/api/cards/{card['id']}/copy", headers=auth_headers)
        assert resp.status_code == 201
        assert resp.json()["archived"] is False

    def test_copy_nonexistent_card_returns_404(self, client, auth_headers):
        resp = client.post("/api/cards/card-doesnotexist/copy", headers=auth_headers)
        assert resp.status_code == 404

    def test_copy_with_time_tracking(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        card = _make_card(
            client, auth_headers, col_id,
            title="Timed Card",
            estimated_hours=8.0,
            actual_hours=3.5,
        )
        resp = client.post(f"/api/cards/{card['id']}/copy", headers=auth_headers)
        assert resp.status_code == 201
        copy = resp.json()
        assert copy["estimated_hours"] == 8.0
        assert copy["actual_hours"] == 3.5


# ══════════════════════════════════════════════════════════════════════════════
# Card Relations
# ══════════════════════════════════════════════════════════════════════════════

class TestCardRelations:
    def test_add_and_list_relation(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        card_a = _make_card(client, auth_headers, col_id, title="Card A")
        card_b = _make_card(client, auth_headers, col_id, title="Card B")

        resp = client.post(
            f"/api/cards/{card_a['id']}/relations",
            json={"related_card_id": card_b["id"], "relation_type": "blocks"},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        relation = resp.json()
        assert relation["relation_type"] == "blocks"
        assert relation["related_card_title"] == "Card B"

        list_resp = client.get(f"/api/cards/{card_a['id']}/relations", headers=auth_headers)
        assert list_resp.status_code == 200
        relations = list_resp.json()
        assert len(relations) == 1
        assert relations[0]["related_card_id"] == card_b["id"]

    def test_all_valid_relation_types(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        for rel_type in ["blocks", "blocked-by", "relates-to", "duplicate-of"]:
            card_a = _make_card(client, auth_headers, col_id, title=f"A-{rel_type}")
            card_b = _make_card(client, auth_headers, col_id, title=f"B-{rel_type}")
            resp = client.post(
                f"/api/cards/{card_a['id']}/relations",
                json={"related_card_id": card_b["id"], "relation_type": rel_type},
                headers=auth_headers,
            )
            assert resp.status_code == 201, f"Failed for {rel_type}: {resp.json()}"

    def test_invalid_relation_type_rejected(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        card_a = _make_card(client, auth_headers, col_id, title="A")
        card_b = _make_card(client, auth_headers, col_id, title="B")
        resp = client.post(
            f"/api/cards/{card_a['id']}/relations",
            json={"related_card_id": card_b["id"], "relation_type": "invalidtype"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_self_relation_rejected(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        card = _make_card(client, auth_headers, col_id, title="Self")
        resp = client.post(
            f"/api/cards/{card['id']}/relations",
            json={"related_card_id": card["id"], "relation_type": "relates-to"},
            headers=auth_headers,
        )
        assert resp.status_code == 400

    def test_duplicate_relation_rejected(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        card_a = _make_card(client, auth_headers, col_id, title="Dup A")
        card_b = _make_card(client, auth_headers, col_id, title="Dup B")
        payload = {"related_card_id": card_b["id"], "relation_type": "relates-to"}
        client.post(f"/api/cards/{card_a['id']}/relations", json=payload, headers=auth_headers)
        resp = client.post(f"/api/cards/{card_a['id']}/relations", json=payload, headers=auth_headers)
        assert resp.status_code == 409

    def test_delete_relation(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        card_a = _make_card(client, auth_headers, col_id, title="Del A")
        card_b = _make_card(client, auth_headers, col_id, title="Del B")
        rel = client.post(
            f"/api/cards/{card_a['id']}/relations",
            json={"related_card_id": card_b["id"], "relation_type": "blocks"},
            headers=auth_headers,
        ).json()

        del_resp = client.delete(
            f"/api/cards/{card_a['id']}/relations/{rel['id']}",
            headers=auth_headers,
        )
        assert del_resp.status_code == 204

        list_resp = client.get(f"/api/cards/{card_a['id']}/relations", headers=auth_headers)
        assert list_resp.json() == []

    def test_delete_nonexistent_relation_returns_404(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        card = _make_card(client, auth_headers, col_id, title="No Rel Card")
        resp = client.delete(f"/api/cards/{card['id']}/relations/9999", headers=auth_headers)
        assert resp.status_code == 404

    def test_cascade_delete_removes_relations(self, client, auth_headers, seeded_board):
        """Deleting a card should cascade-delete its relations."""
        _, col_id = seeded_board
        card_a = _make_card(client, auth_headers, col_id, title="Cascade A")
        card_b = _make_card(client, auth_headers, col_id, title="Cascade B")
        rel = client.post(
            f"/api/cards/{card_a['id']}/relations",
            json={"related_card_id": card_b["id"], "relation_type": "blocks"},
            headers=auth_headers,
        ).json()

        client.delete(f"/api/cards/{card_a['id']}", headers=auth_headers)

        # card_a is gone, its relations should be gone too
        # card_b still exists, verify by checking it has no relations
        list_resp = client.get(f"/api/cards/{card_b['id']}/relations", headers=auth_headers)
        assert list_resp.status_code == 200
        assert list_resp.json() == []


# ══════════════════════════════════════════════════════════════════════════════
# Global Search
# ══════════════════════════════════════════════════════════════════════════════

class TestSearch:
    def test_search_by_title(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        _make_card(client, auth_headers, col_id, title="Unique Searchable Title XYZ")

        resp = client.get("/api/search?q=XYZ", headers=auth_headers)
        assert resp.status_code == 200
        results = resp.json()
        assert any(r["title"] == "Unique Searchable Title XYZ" for r in results)

    def test_search_by_details(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        _make_card(
            client, auth_headers, col_id,
            title="Details Search Card",
            details="UNIQUE_DETAIL_TOKEN_QQQ",
        )

        resp = client.get("/api/search?q=UNIQUE_DETAIL_TOKEN_QQQ", headers=auth_headers)
        assert resp.status_code == 200
        results = resp.json()
        assert any(r["title"] == "Details Search Card" for r in results)

    def test_search_is_case_insensitive(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        _make_card(client, auth_headers, col_id, title="CaseTest Card ZZXXYY")

        resp = client.get("/api/search?q=casetest", headers=auth_headers)
        assert resp.status_code == 200
        results = resp.json()
        assert any("CaseTest" in r["title"] for r in results)

    def test_search_excludes_archived_by_default(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        card = _make_card(client, auth_headers, col_id, title="Archived Search Card AABBCC")
        client.put(f"/api/cards/{card['id']}/archive", headers=auth_headers)

        resp = client.get("/api/search?q=AABBCC", headers=auth_headers)
        assert resp.status_code == 200
        results = resp.json()
        assert not any(r["id"] == card["id"] for r in results)

    def test_search_includes_archived_when_requested(self, client, auth_headers, seeded_board):
        _, col_id = seeded_board
        card = _make_card(client, auth_headers, col_id, title="Archived Visible DDEEFF")
        client.put(f"/api/cards/{card['id']}/archive", headers=auth_headers)

        resp = client.get(
            "/api/search?q=DDEEFF&include_archived=true", headers=auth_headers
        )
        assert resp.status_code == 200
        results = resp.json()
        found = next((r for r in results if r["id"] == card["id"]), None)
        assert found is not None
        assert found["archived"] is True

    def test_search_returns_board_and_column_info(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        _make_card(client, auth_headers, col_id, title="InfoCard UNIQUE99")

        resp = client.get("/api/search?q=UNIQUE99", headers=auth_headers)
        assert resp.status_code == 200
        result = resp.json()[0]
        assert result["board_id"] == board_id
        assert "board_title" in result
        assert "column_title" in result

    def test_search_does_not_return_other_users_cards(self, client, seeded_board):
        import uuid
        # Create a second user
        other_user = f"other_{uuid.uuid4().hex[:6]}"
        other_resp = client.post(
            "/api/auth/register",
            json={"username": other_user, "password": "pass123"},
        )
        other_headers = {"Authorization": f"Bearer {other_resp.json()['access_token']}"}

        # Get other user's board/col and create a card
        other_boards = client.get("/api/boards", headers=other_headers).json()
        other_board_id = other_boards[0]["id"]
        other_board = client.get(f"/api/boards/{other_board_id}", headers=other_headers).json()
        other_col_id = other_board["columns"][0]["id"]
        _make_card(client, other_headers, other_col_id, title="PrivateCard SECRETTOKEN999")

        # First user should NOT see it
        first_resp = client.post(
            "/api/auth/register",
            json={"username": f"first_{uuid.uuid4().hex[:6]}", "password": "pass123"},
        )
        first_headers = {"Authorization": f"Bearer {first_resp.json()['access_token']}"}
        search_resp = client.get("/api/search?q=SECRETTOKEN999", headers=first_headers)
        assert search_resp.status_code == 200
        assert search_resp.json() == []

    def test_search_requires_auth(self, client):
        resp = client.get("/api/search?q=test")
        assert resp.status_code == 401

    def test_search_empty_query_returns_422(self, client, auth_headers):
        resp = client.get("/api/search?q=", headers=auth_headers)
        assert resp.status_code == 422


# ══════════════════════════════════════════════════════════════════════════════
# Time Tracking
# ══════════════════════════════════════════════════════════════════════════════

class TestTimeTracking:
    def test_create_card_with_time_tracking(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        card = _make_card(
            client, auth_headers, col_id,
            title="Timed Task",
            estimated_hours=16.0,
            actual_hours=4.5,
        )
        assert card["estimated_hours"] == 16.0
        assert card["actual_hours"] == 4.5

    def test_time_tracking_appears_in_board(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        card = _make_card(
            client, auth_headers, col_id,
            title="Board Time Card",
            estimated_hours=8.0,
        )
        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        board_card = board["cards"][card["id"]]
        assert board_card["estimated_hours"] == 8.0
        assert board_card["actual_hours"] is None

    def test_update_card_time_tracking(self, client, auth_headers, seeded_board):
        board_id, col_id = seeded_board
        card = _make_card(client, auth_headers, col_id, title="Update Time Card")

        # Get current card order from the board
        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        col = next(c for c in board["columns"] if c["id"] == col_id)
        order = col["cardIds"].index(card["id"])

        update_resp = client.put(
            f"/api/cards/{card['id']}",
            json={
                "column_id": col_id,
                "order": order,
                "estimated_hours": 12.0,
                "actual_hours": 7.0,
            },
            headers=auth_headers,
        )
        assert update_resp.status_code == 200

        board = client.get(f"/api/boards/{board_id}", headers=auth_headers).json()
        board_card = board["cards"][card["id"]]
        assert board_card["estimated_hours"] == 12.0
        assert board_card["actual_hours"] == 7.0
