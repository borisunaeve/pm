import uuid

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import CreateCardRequest, UpdateCardRequest

router = APIRouter(prefix="/api/cards", tags=["cards"])


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


def _get_board_id_for_column(cursor, column_id: str) -> str:
    cursor.execute("SELECT board_id FROM columns WHERE id = ?", (column_id,))
    row = cursor.fetchone()
    return row["board_id"] if row else ""


def _log_activity(cursor, board_id: str, user_id: str, action: str, entity_type: str, entity_title: str):
    cursor.execute(
        "INSERT INTO board_activity (board_id, user_id, action, entity_type, entity_title) VALUES (?, ?, ?, ?, ?)",
        (board_id, user_id, action, entity_type, entity_title),
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
        "INSERT INTO cards (id, column_id, title, details, [order], priority, due_date, labels, assignee_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (new_id, request.column_id, request.title, request.details, next_order,
         request.priority or "medium", request.due_date, request.labels or "", request.assignee_id),
    )

    board_id = _get_board_id_for_column(cursor, request.column_id)
    _log_activity(cursor, board_id, current_user["sub"], "created", "card", request.title)
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

    updates.append("column_id = ?")
    params.append(request.column_id)
    updates.append("[order] = ?")
    params.append(request.order)

    params.append(card_id)

    query = f"UPDATE cards SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, tuple(params))

    # Log if title was updated
    if request.title:
        board_id = _get_board_id_for_column(cursor, request.column_id)
        _log_activity(cursor, board_id, current_user["sub"], "updated", "card", request.title)

    conn.commit()
    conn.close()
    return {"status": "success"}


@router.delete("/{card_id}", status_code=204)
def delete_card(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT c.id, c.title, col.board_id FROM cards c
           JOIN columns col ON col.id = c.column_id
           JOIN boards b ON b.id = col.board_id
           WHERE c.id = ? AND (b.user_id = ? OR
               b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (card_id, current_user["sub"], current_user["sub"]),
    )
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Card not found")

    _log_activity(cursor, row["board_id"], current_user["sub"], "deleted", "card", row["title"])
    cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()
