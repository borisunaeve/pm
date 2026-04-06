import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import CardActivityEntry, CreateCardRequest, UpdateCardRequest
from backend.notify import notify_watchers

router = APIRouter(prefix="/api/cards", tags=["cards"])

# Fields to track in card activity (excludes order, column_id handled specially)
_TRACKED_FIELDS = ("title", "priority", "due_date", "labels", "assignee_id",
                   "estimated_hours", "actual_hours", "sprint_id")


def _assert_column_access(cursor, column_id: str, user_id: str):
    """Allow board owner OR board member to write to cards."""
    cursor.execute(
        """SELECT col.id FROM columns col JOIN boards b ON b.id = col.board_id
           WHERE col.id = ? AND (b.user_id = ? OR
               b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (column_id, user_id, user_id),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Column not found")


def _assert_card_access(cursor, card_id: str, user_id: str):
    """Allow board owner OR member to access this card. Returns the card row."""
    cursor.execute(
        """SELECT c.id, c.title, c.column_id, col.board_id FROM cards c
           JOIN columns col ON col.id = c.column_id
           JOIN boards b ON b.id = col.board_id
           WHERE c.id = ? AND (b.user_id = ? OR
               b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (card_id, user_id, user_id),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Card not found")
    return row


def _get_board_id_for_column(cursor, column_id: str) -> str:
    cursor.execute("SELECT board_id FROM columns WHERE id = ?", (column_id,))
    row = cursor.fetchone()
    return row["board_id"] if row else ""


def _log_activity(cursor, board_id: str, user_id: str, action: str, entity_type: str, entity_title: str):
    cursor.execute(
        "INSERT INTO board_activity (board_id, user_id, action, entity_type, entity_title) VALUES (?, ?, ?, ?, ?)",
        (board_id, user_id, action, entity_type, entity_title),
    )


def _log_card_activity(cursor, card_id: str, user_id: str, field: str, old_value, new_value):
    """Log a field-level change on a card."""
    cursor.execute(
        "INSERT INTO card_activity (card_id, user_id, field, old_value, new_value) VALUES (?, ?, ?, ?, ?)",
        (card_id, user_id, field, str(old_value) if old_value is not None else None,
         str(new_value) if new_value is not None else None),
    )


@router.post("", status_code=201)
def create_card(request: CreateCardRequest, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_column_access(cursor, request.column_id, current_user["sub"])

    new_id = f"card-{uuid.uuid4().hex[:8]}"

    cursor.execute(
        "SELECT MAX([order]) as max_o FROM cards WHERE column_id = ?",
        (request.column_id,),
    )
    row = cursor.fetchone()
    next_order = (row["max_o"] + 1) if row["max_o"] is not None else 0

    cursor.execute(
        """INSERT INTO cards
           (id, column_id, title, details, [order], priority, due_date, labels, assignee_id, estimated_hours, actual_hours, sprint_id, color)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (new_id, request.column_id, request.title, request.details, next_order,
         request.priority or "medium", request.due_date, request.labels or "",
         request.assignee_id, request.estimated_hours, request.actual_hours, request.sprint_id,
         request.color),
    )

    board_id = _get_board_id_for_column(cursor, request.column_id)
    _log_activity(cursor, board_id, current_user["sub"], "created", "card", request.title)

    # Auto-watch: the creator watches the card; if assignee != creator, notify assignee
    cursor.execute(
        "INSERT OR IGNORE INTO card_watchers (card_id, user_id) VALUES (?, ?)",
        (new_id, current_user["sub"]),
    )
    if request.assignee_id and request.assignee_id != current_user["sub"]:
        cursor.execute(
            "INSERT OR IGNORE INTO card_watchers (card_id, user_id) VALUES (?, ?)",
            (new_id, request.assignee_id),
        )
        cursor.execute("SELECT username FROM users WHERE id = ?", (current_user["sub"],))
        actor_row = cursor.fetchone()
        actor_name = actor_row["username"] if actor_row else "Someone"
        cursor.execute(
            """INSERT INTO user_notifications (user_id, board_id, card_id, type, message)
               VALUES (?, ?, ?, ?, ?)""",
            (request.assignee_id, board_id, new_id, "assigned",
             f"{actor_name} assigned you to \"{request.title}\""),
        )

    conn.commit()
    conn.close()
    return {
        "id": new_id,
        "title": request.title,
        "details": request.details,
        "column_id": request.column_id,
        "priority": request.priority or "medium",
        "due_date": request.due_date,
        "labels": request.labels or "",
        "assignee_id": request.assignee_id,
        "assignee_username": None,
        "archived": False,
        "estimated_hours": request.estimated_hours,
        "actual_hours": request.actual_hours,
        "sprint_id": request.sprint_id,
        "parent_card_id": request.parent_card_id,
        "subtask_count": 0,
        "color": request.color,
    }


@router.put("/{card_id}")
def update_card(
    card_id: str,
    request: UpdateCardRequest,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_column_access(cursor, request.column_id, current_user["sub"])

    # Fetch existing values for activity logging
    cursor.execute("SELECT * FROM cards WHERE id = ?", (card_id,))
    existing = cursor.fetchone()

    updates = []
    params = []

    if request.title is not None:
        updates.append("title = ?")
        params.append(request.title)
    if request.details is not None:
        updates.append("details = ?")
        params.append(request.details)
    if request.priority is not None:
        updates.append("priority = ?")
        params.append(request.priority)
    if request.due_date is not None:
        updates.append("due_date = ?")
        params.append(request.due_date)
    if request.labels is not None:
        updates.append("labels = ?")
        params.append(request.labels)
    if request.assignee_id is not None:
        updates.append("assignee_id = ?")
        params.append(request.assignee_id)
    if request.estimated_hours is not None:
        updates.append("estimated_hours = ?")
        params.append(request.estimated_hours)
    if request.actual_hours is not None:
        updates.append("actual_hours = ?")
        params.append(request.actual_hours)
    if request.sprint_id is not None:
        updates.append("sprint_id = ?")
        params.append(request.sprint_id if request.sprint_id != "" else None)
    if request.parent_card_id is not None:
        updates.append("parent_card_id = ?")
        params.append(request.parent_card_id if request.parent_card_id != "" else None)
    if request.color is not None:
        updates.append("color = ?")
        params.append(request.color if request.color != "" else None)

    updates.append("column_id = ?")
    params.append(request.column_id)
    updates.append("[order] = ?")
    params.append(request.order)

    params.append(card_id)

    query = f"UPDATE cards SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, tuple(params))

    # Log field-level changes for meaningful fields
    if existing:
        for field in _TRACKED_FIELDS:
            new_val = getattr(request, field, None)
            if new_val is None:
                continue
            old_val = existing[field] if field in existing.keys() else None
            if str(old_val or "") != str(new_val or ""):
                _log_card_activity(cursor, card_id, current_user["sub"], field, old_val, new_val)

        # Log column moves separately
        if existing["column_id"] != request.column_id:
            cursor.execute("SELECT title FROM columns WHERE id = ?", (existing["column_id"],))
            old_col = cursor.fetchone()
            cursor.execute("SELECT title FROM columns WHERE id = ?", (request.column_id,))
            new_col = cursor.fetchone()
            _log_card_activity(
                cursor, card_id, current_user["sub"], "column",
                old_col["title"] if old_col else existing["column_id"],
                new_col["title"] if new_col else request.column_id,
            )

    board_id = _get_board_id_for_column(cursor, request.column_id)
    card_title = request.title if request.title else (existing["title"] if existing else "card")
    if request.title:
        _log_activity(cursor, board_id, current_user["sub"], "updated", "card", request.title)

    # Notify watchers of this card (excluding the person making the change)
    cursor.execute("SELECT username FROM users WHERE id = ?", (current_user["sub"],))
    actor_row = cursor.fetchone()
    actor_name = actor_row["username"] if actor_row else "Someone"
    notify_watchers(
        cursor, card_id, current_user["sub"],
        "card_updated",
        f"{actor_name} updated \"{card_title}\"",
        board_id=board_id,
    )

    conn.commit()
    conn.close()
    return {"status": "success"}


@router.get("/{card_id}/activity", response_model=List[CardActivityEntry])
def get_card_activity(
    card_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])
    cursor.execute(
        """SELECT ca.id, ca.card_id, ca.user_id, u.username, ca.field,
                  ca.old_value, ca.new_value, ca.created_at
           FROM card_activity ca JOIN users u ON u.id = ca.user_id
           WHERE ca.card_id = ?
           ORDER BY ca.created_at DESC LIMIT ?""",
        (card_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        CardActivityEntry(
            id=r["id"], card_id=r["card_id"], user_id=r["user_id"],
            username=r["username"], field=r["field"],
            old_value=r["old_value"], new_value=r["new_value"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


@router.delete("/{card_id}", status_code=204)
def delete_card(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()

    row = _assert_card_access(cursor, card_id, current_user["sub"])
    _log_activity(cursor, row["board_id"], current_user["sub"], "deleted", "card", row["title"])
    cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()


@router.put("/{card_id}/archive", status_code=200)
def archive_card(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()

    row = _assert_card_access(cursor, card_id, current_user["sub"])
    cursor.execute("UPDATE cards SET archived = 1 WHERE id = ?", (card_id,))
    _log_activity(cursor, row["board_id"], current_user["sub"], "archived", "card", row["title"])
    conn.commit()
    conn.close()
    return {"status": "archived"}


@router.put("/{card_id}/restore", status_code=200)
def restore_card(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()

    row = _assert_card_access(cursor, card_id, current_user["sub"])
    cursor.execute("UPDATE cards SET archived = 0 WHERE id = ?", (card_id,))
    _log_activity(cursor, row["board_id"], current_user["sub"], "restored", "card", row["title"])
    conn.commit()
    conn.close()
    return {"status": "restored"}


@router.post("/{card_id}/copy", status_code=201)
def copy_card(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()

    row = _assert_card_access(cursor, card_id, current_user["sub"])

    cursor.execute(
        "SELECT * FROM cards WHERE id = ?", (card_id,)
    )
    src = cursor.fetchone()

    new_id = f"card-{uuid.uuid4().hex[:8]}"
    cursor.execute(
        "SELECT MAX([order]) as max_o FROM cards WHERE column_id = ?",
        (src["column_id"],),
    )
    max_row = cursor.fetchone()
    next_order = (max_row["max_o"] + 1) if max_row["max_o"] is not None else 0

    cursor.execute(
        """INSERT INTO cards
           (id, column_id, title, details, [order], priority, due_date, labels, assignee_id, estimated_hours, actual_hours)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (new_id, src["column_id"], f"{src['title']} (copy)", src["details"],
         next_order, src["priority"], src["due_date"], src["labels"],
         src["assignee_id"], src["estimated_hours"], src["actual_hours"]),
    )
    _log_activity(cursor, row["board_id"], current_user["sub"], "created", "card", f"{src['title']} (copy)")
    conn.commit()
    conn.close()
    return {
        "id": new_id,
        "title": f"{src['title']} (copy)",
        "details": src["details"],
        "column_id": src["column_id"],
        "priority": src["priority"],
        "due_date": src["due_date"],
        "labels": src["labels"],
        "assignee_id": src["assignee_id"],
        "archived": False,
        "estimated_hours": src["estimated_hours"],
        "actual_hours": src["actual_hours"],
    }
