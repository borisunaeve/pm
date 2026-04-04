import uuid

from fastapi import APIRouter

from backend.database import get_db_connection
from backend.models import CreateCardRequest, UpdateCardRequest

router = APIRouter(prefix="/api/cards", tags=["cards"])


@router.post("")
def create_card(request: CreateCardRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    new_id = f"card-{uuid.uuid4().hex[:8]}"

    cursor.execute(
        "SELECT MAX([order]) as max_o FROM cards WHERE column_id = ?",
        (request.column_id,),
    )
    row = cursor.fetchone()
    next_order = (row["max_o"] + 1) if row["max_o"] is not None else 0

    cursor.execute(
        "INSERT INTO cards (id, column_id, title, details, [order]) VALUES (?, ?, ?, ?, ?)",
        (new_id, request.column_id, request.title, request.details, next_order),
    )
    conn.commit()
    conn.close()
    return {"id": new_id, "title": request.title, "details": request.details, "column_id": request.column_id}


@router.put("/{card_id}")
def update_card(card_id: str, request: UpdateCardRequest):
    conn = get_db_connection()
    cursor = conn.cursor()

    updates = []
    params = []
    if request.title is not None:
        updates.append("title = ?")
        params.append(request.title)
    if request.details is not None:
        updates.append("details = ?")
        params.append(request.details)

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


@router.delete("/{card_id}")
def delete_card(card_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
    conn.commit()
    conn.close()
    return {"status": "success"}
