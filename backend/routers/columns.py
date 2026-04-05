import uuid

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import CreateColumnRequest, ReorderColumnsRequest, UpdateColumnRequest

router = APIRouter(prefix="/api/columns", tags=["columns"])


def _assert_board_access(cursor, board_id: str, user_id: str):
    """Allow owner or member."""
    cursor.execute(
        """SELECT id FROM boards WHERE id = ? AND (
            user_id = ? OR
            id IN (SELECT board_id FROM board_members WHERE user_id = ?)
        )""",
        (board_id, user_id, user_id),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Board not found")


def _assert_column_access(cursor, column_id: str, user_id: str):
    cursor.execute(
        """SELECT c.id FROM columns c JOIN boards b ON b.id = c.board_id
           WHERE c.id = ? AND (b.user_id = ? OR
               b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (column_id, user_id, user_id),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Column not found")


@router.post("", status_code=201)
def create_column(request: CreateColumnRequest, current_user: dict = Depends(get_current_user)):
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_board_access(cursor, request.board_id, current_user["sub"])

    cursor.execute(
        "SELECT MAX([order]) as max_o FROM columns WHERE board_id = ?",
        (request.board_id,),
    )
    row = cursor.fetchone()
    next_order = (row["max_o"] + 1) if row["max_o"] is not None else 0

    col_id = f"col-{uuid.uuid4().hex[:8]}"
    cursor.execute(
        "INSERT INTO columns (id, board_id, title, [order], wip_limit) VALUES (?, ?, ?, ?, ?)",
        (col_id, request.board_id, request.title.strip(), next_order, request.wip_limit),
    )
    conn.commit()
    conn.close()
    return {"id": col_id, "title": request.title.strip(), "board_id": request.board_id,
            "order": next_order, "wip_limit": request.wip_limit}


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
    _assert_column_access(cursor, column_id, current_user["sub"])

    cursor.execute(
        "UPDATE columns SET title = ?, wip_limit = ? WHERE id = ?",
        (request.title.strip(), request.wip_limit, column_id),
    )
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.delete("/{column_id}", status_code=204)
def delete_column(column_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_column_access(cursor, column_id, current_user["sub"])
    cursor.execute("DELETE FROM columns WHERE id = ?", (column_id,))
    conn.commit()
    conn.close()


@router.post("/reorder")
def reorder_columns(request: ReorderColumnsRequest, current_user: dict = Depends(get_current_user)):
    """Persist new column order: column_ids in desired order."""
    if not request.column_ids:
        raise HTTPException(status_code=400, detail="column_ids cannot be empty")

    conn = get_db_connection()
    cursor = conn.cursor()

    # Verify access to all columns (they must all belong to a board the user can access)
    placeholders = ",".join("?" * len(request.column_ids))
    cursor.execute(
        f"""SELECT c.id FROM columns c JOIN boards b ON b.id = c.board_id
            WHERE c.id IN ({placeholders}) AND (
                b.user_id = ? OR
                b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (*request.column_ids, current_user["sub"], current_user["sub"]),
    )
    accessible = {row["id"] for row in cursor.fetchall()}
    for col_id in request.column_ids:
        if col_id not in accessible:
            conn.close()
            raise HTTPException(status_code=404, detail=f"Column {col_id} not found")

    for idx, col_id in enumerate(request.column_ids):
        cursor.execute("UPDATE columns SET [order] = ? WHERE id = ?", (idx, col_id))

    conn.commit()
    conn.close()
    return {"status": "success"}
