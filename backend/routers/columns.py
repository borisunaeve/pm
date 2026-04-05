import uuid

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import CreateColumnRequest, UpdateColumnRequest

router = APIRouter(prefix="/api/columns", tags=["columns"])


def _assert_board_owner(cursor, board_id: str, user_id: str):
    cursor.execute("SELECT id FROM boards WHERE id = ? AND user_id = ?", (board_id, user_id))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Board not found")


@router.post("", status_code=201)
def create_column(request: CreateColumnRequest, current_user: dict = Depends(get_current_user)):
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_board_owner(cursor, request.board_id, current_user["sub"])

    cursor.execute(
        "SELECT MAX([order]) as max_o FROM columns WHERE board_id = ?",
        (request.board_id,),
    )
    row = cursor.fetchone()
    next_order = (row["max_o"] + 1) if row["max_o"] is not None else 0

    col_id = f"col-{uuid.uuid4().hex[:8]}"
    cursor.execute(
        "INSERT INTO columns (id, board_id, title, [order]) VALUES (?, ?, ?, ?)",
        (col_id, request.board_id, request.title.strip(), next_order),
    )
    conn.commit()
    conn.close()
    return {"id": col_id, "title": request.title.strip(), "board_id": request.board_id, "order": next_order}


@router.put("/{column_id}")
def update_column(
    column_id: str,
    request: UpdateColumnRequest,
    current_user: dict = Depends(get_current_user),
):
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify ownership via board
    cursor.execute(
        "SELECT c.id FROM columns c JOIN boards b ON b.id = c.board_id WHERE c.id = ? AND b.user_id = ?",
        (column_id, current_user["sub"]),
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Column not found")

    cursor.execute("UPDATE columns SET title = ? WHERE id = ?", (request.title.strip(), column_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.delete("/{column_id}", status_code=204)
def delete_column(column_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT c.id FROM columns c JOIN boards b ON b.id = c.board_id WHERE c.id = ? AND b.user_id = ?",
        (column_id, current_user["sub"]),
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Column not found")

    cursor.execute("DELETE FROM columns WHERE id = ?", (column_id,))
    conn.commit()
    conn.close()
