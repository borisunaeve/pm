"""
Tests for iteration 6 features:
  - Sub-tasks (GET/POST /api/cards/{id}/subtasks)
  - @mentions in comments
  - parent_card_id field propagated through board data
"""
import uuid
import pytest


# ── Helpers ────────────────────────────────────────────────────────────────────

def make_user(client, prefix="u6"):
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


def post_comment(client, headers, card_id, content):
    resp = client.post(f"/api/cards/{card_id}/comments", json={"content": content}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


# ══════════════════════════════════════════════════════════════════════════════
# Sub-tasks
# ══════════════════════════════════════════════════════════════════════════════

class TestSubtasks:
    def test_list_subtasks_empty(self, client):
        h, uid, uname = make_user(client, "st1")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id, "Parent card")
        resp = client.get(f"/api/cards/{card['id']}/subtasks", headers=h)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_create_subtask(self, client):
        h, uid, uname = make_user(client, "st2")
        board_id, col_id = get_board_and_col(client, h)
        parent = create_card(client, h, col_id, "Parent")
        resp = client.post(f"/api/cards/{parent['id']}/subtasks",
                           json={"title": "Sub-task A"}, headers=h)
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "Sub-task A"
        assert data["parent_card_id"] == parent["id"]

    def test_subtask_appears_in_list(self, client):
        h, uid, uname = make_user(client, "st3")
        board_id, col_id = get_board_and_col(client, h)
        parent = create_card(client, h, col_id, "Parent")
        client.post(f"/api/cards/{parent['id']}/subtasks",
                    json={"title": "Sub A"}, headers=h)
        client.post(f"/api/cards/{parent['id']}/subtasks",
                    json={"title": "Sub B"}, headers=h)
        subs = client.get(f"/api/cards/{parent['id']}/subtasks", headers=h).json()
        assert len(subs) == 2
        titles = {s["title"] for s in subs}
        assert titles == {"Sub A", "Sub B"}

    def test_subtask_count_on_board(self, client):
        h, uid, uname = make_user(client, "st4")
        board_id, col_id = get_board_and_col(client, h)
        parent = create_card(client, h, col_id, "Parent with subs")
        client.post(f"/api/cards/{parent['id']}/subtasks",
                    json={"title": "Sub 1"}, headers=h)
        client.post(f"/api/cards/{parent['id']}/subtasks",
                    json={"title": "Sub 2"}, headers=h)
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        parent_card = board["cards"][parent["id"]]
        assert parent_card["subtask_count"] == 2

    def test_subtask_with_all_fields(self, client):
        h, uid, uname = make_user(client, "st5")
        board_id, col_id = get_board_and_col(client, h)
        parent = create_card(client, h, col_id, "Parent")
        resp = client.post(
            f"/api/cards/{parent['id']}/subtasks",
            json={"title": "Detailed sub", "priority": "high", "due_date": "2030-01-01",
                  "assignee_id": uid},
            headers=h,
        )
        data = resp.json()
        assert data["priority"] == "high"
        assert data["due_date"] == "2030-01-01"
        assert data["assignee_id"] == uid

    def test_subtask_lives_in_same_column(self, client):
        h, uid, uname = make_user(client, "st6")
        board_id, col_id = get_board_and_col(client, h)
        parent = create_card(client, h, col_id, "Parent")
        sub_resp = client.post(f"/api/cards/{parent['id']}/subtasks",
                               json={"title": "Sub"}, headers=h)
        # Sub-task should appear in the board's column cards
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        col = next(c for c in board["columns"] if c["id"] == col_id)
        assert sub_resp.json()["id"] in col["cardIds"]

    def test_archived_subtask_excluded_from_count(self, client):
        h, uid, uname = make_user(client, "st7")
        board_id, col_id = get_board_and_col(client, h)
        parent = create_card(client, h, col_id, "Parent")
        sub = client.post(f"/api/cards/{parent['id']}/subtasks",
                          json={"title": "Sub"}, headers=h).json()
        client.put(f"/api/cards/{sub['id']}/archive", headers=h)
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        assert board["cards"][parent["id"]]["subtask_count"] == 0

    def test_subtask_list_requires_auth(self, client):
        h, uid, uname = make_user(client, "st8")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id)
        resp = client.get(f"/api/cards/{card['id']}/subtasks")
        assert resp.status_code == 401

    def test_subtask_create_requires_auth(self, client):
        h, uid, uname = make_user(client, "st9")
        board_id, col_id = get_board_and_col(client, h)
        card = create_card(client, h, col_id)
        resp = client.post(f"/api/cards/{card['id']}/subtasks",
                           json={"title": "Sub"})
        assert resp.status_code == 401

    def test_subtask_isolation_between_users(self, client):
        h1, uid1, uname1 = make_user(client, "st10a")
        h2, uid2, uname2 = make_user(client, "st10b")
        board_id1, col_id1 = get_board_and_col(client, h1)
        card = create_card(client, h1, col_id1)
        resp = client.get(f"/api/cards/{card['id']}/subtasks", headers=h2)
        assert resp.status_code == 404

    def test_board_data_includes_parent_card_id(self, client):
        h, uid, uname = make_user(client, "st11")
        board_id, col_id = get_board_and_col(client, h)
        parent = create_card(client, h, col_id, "Parent")
        sub = client.post(f"/api/cards/{parent['id']}/subtasks",
                          json={"title": "Sub"}, headers=h).json()
        board = client.get(f"/api/boards/{board_id}", headers=h).json()
        sub_from_board = board["cards"].get(sub["id"])
        assert sub_from_board is not None
        assert sub_from_board["parent_card_id"] == parent["id"]


# ══════════════════════════════════════════════════════════════════════════════
# @Mentions in comments
# ══════════════════════════════════════════════════════════════════════════════

class TestMentions:
    def _setup(self, client, prefix="mn"):
        h1, uid1, uname1 = make_user(client, f"{prefix}a")
        h2, uid2, uname2 = make_user(client, f"{prefix}b")
        boards = client.get("/api/boards", headers=h1).json()
        board_id = boards[0]["id"]
        col_id = client.get(f"/api/boards/{board_id}", headers=h1).json()["columns"][0]["id"]
        # Invite user2 to board
        client.post(f"/api/boards/{board_id}/members", json={"username": uname2}, headers=h1)
        card = create_card(client, h1, col_id)
        return h1, h2, uid1, uid2, uname1, uname2, board_id, col_id, card

    def test_mention_creates_notification(self, client):
        h1, h2, uid1, uid2, un1, un2, bid, cid, card = self._setup(client, "mna")
        post_comment(client, h1, card["id"], f"Hey @{un2} check this out")
        notifs = client.get("/api/notifications", headers=h2).json()
        assert any(n["type"] == "mentioned" for n in notifs)

    def test_mention_notification_has_correct_message(self, client):
        h1, h2, uid1, uid2, un1, un2, bid, cid, card = self._setup(client, "mnb")
        post_comment(client, h1, card["id"], f"@{un2} please review")
        notifs = client.get("/api/notifications", headers=h2).json()
        mention = next((n for n in notifs if n["type"] == "mentioned"), None)
        assert mention is not None
        assert un1 in mention["message"]

    def test_mention_auto_watches_card(self, client):
        h1, h2, uid1, uid2, un1, un2, bid, cid, card = self._setup(client, "mnc")
        post_comment(client, h1, card["id"], f"@{un2} look at this")
        status = client.get(f"/api/cards/{card['id']}/watch/status", headers=h2).json()
        assert status["watching"] is True

    def test_mention_non_member_ignored(self, client):
        h1, uid1, uname1 = make_user(client, "mnd_owner")
        h3, uid3, uname3 = make_user(client, "mnd_outsider")
        boards = client.get("/api/boards", headers=h1).json()
        board_id = boards[0]["id"]
        col_id = client.get(f"/api/boards/{board_id}", headers=h1).json()["columns"][0]["id"]
        card = create_card(client, h1, col_id)
        # Mention someone NOT on the board — should not create notification
        post_comment(client, h1, card["id"], f"@{uname3} hello")
        notifs = client.get("/api/notifications", headers=h3).json()
        assert not any(n["type"] == "mentioned" for n in notifs)

    def test_self_mention_ignored(self, client):
        h1, uid1, uname1 = make_user(client, "mne")
        boards = client.get("/api/boards", headers=h1).json()
        board_id = boards[0]["id"]
        col_id = client.get(f"/api/boards/{board_id}", headers=h1).json()["columns"][0]["id"]
        card = create_card(client, h1, col_id)
        # Mentioning yourself should not create notification
        initial_count = len(client.get("/api/notifications", headers=h1).json())
        post_comment(client, h1, card["id"], f"@{uname1} note to self")
        after_count = len(client.get("/api/notifications", headers=h1).json())
        mention_notifs = [
            n for n in client.get("/api/notifications", headers=h1).json()
            if n["type"] == "mentioned"
        ]
        assert len(mention_notifs) == 0

    def test_multiple_mentions_in_one_comment(self, client):
        h1, h2, uid1, uid2, un1, un2, bid, cid, card = self._setup(client, "mnf")
        h3, uid3, un3 = make_user(client, "mnf_extra")
        # Invite user3 to board too
        client.post(f"/api/boards/{bid}/members", json={"username": un3}, headers=h1)
        post_comment(client, h1, card["id"], f"@{un2} and @{un3} both check this")
        n2 = client.get("/api/notifications", headers=h2).json()
        n3 = client.get("/api/notifications", headers=h3).json()
        assert any(x["type"] == "mentioned" for x in n2)
        assert any(x["type"] == "mentioned" for x in n3)

    def test_comment_has_display_name(self, client):
        h1, uid1, uname1 = make_user(client, "mng")
        boards = client.get("/api/boards", headers=h1).json()
        board_id = boards[0]["id"]
        col_id = client.get(f"/api/boards/{board_id}", headers=h1).json()["columns"][0]["id"]
        # Set display name
        client.put("/api/auth/me", json={"display_name": "Display Person"}, headers=h1)
        card = create_card(client, h1, col_id)
        comment = post_comment(client, h1, card["id"], "Hello world")
        assert "display_name" in comment
        assert comment["display_name"] == "Display Person"

    def test_list_comments_includes_display_name(self, client):
        h1, uid1, uname1 = make_user(client, "mnh")
        boards = client.get("/api/boards", headers=h1).json()
        board_id = boards[0]["id"]
        col_id = client.get(f"/api/boards/{board_id}", headers=h1).json()["columns"][0]["id"]
        client.put("/api/auth/me", json={"display_name": "Listed Person"}, headers=h1)
        card = create_card(client, h1, col_id)
        post_comment(client, h1, card["id"], "Test comment")
        comments = client.get(f"/api/cards/{card['id']}/comments", headers=h1).json()
        assert comments[0]["display_name"] == "Listed Person"
