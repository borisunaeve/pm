import uuid

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import CreateCardRequest, UpdateCardRequest

router = APIRouter(prefix="/api/cards", tags=["cards"])


def _assert_column_owner(cursor, column_id: str, user_id: str):
    cursor.execute(
        "SELECT col.id FROM columns col JOIN boards b ON b.id = col.board_id WHERE col.id = ? AND b.user_id = ?",
        (column_id, user_id),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Column not found")


@router.post("", status_code=201)
def create_card(request: CreateCardRequest, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_column_owner(cursor, request.column_id, current_user["sub"])

    new_id = f"card-{uuid.uuid4().hex[:8]}"

    cursor.execute(
        "SELECT MAX([order]) as max_o FROM cards WHERE column_id = ?",
        (request.column_id,),
    )
    row = cursor.fetchone()
    next_order = (row["max_o"] + 1) if row["max_o"] is not None else 0

    cursor.execute(
        "INSERT INTO cards (id, column_id, title, details, [order], priority, due_date, labels) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (new_id, request.column_id, request.title, request.details, next_order,
         request.priority or "medium", request.due_date, request.labels or ""),
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
    }


@router.put("/{card_id}")
def update_card(
    card_id: str,
    request: UpdateCardRequest,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify ownership — check the target column belongs to the user
    _assert_column_owner(cursor, request.column_id, current_user["sub"])

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

    updates.append("column_id = ?")
    params.append(request.column_id)
    updates.append("[order] = ?")
    params.append(request.order)

    params.append(card_id)

    query = f"UPDATE cards SET {', '.join(updates)} WHERE id = ?"
    cursor.execute(query, tuple(params))
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.delete("/{card_id}", status_code=204)
def delete_card(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify ownership
    cursor.execute(
        """
        SELECT c.id FROM cards c
        JOIN columns col ON col.id = c.column_id
        JOIN boards b ON b.id = col.board_id
        WHERE c.id = ? AND b.user_id = ?
        """,
        (card_id, current_user["sub"]),
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Card not found")

    cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()
