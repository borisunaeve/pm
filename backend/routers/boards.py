import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import BoardData, BoardSummary, CardModel, ColumnModel, CreateBoardRequest, UpdateBoardRequest

router = APIRouter(prefix="/api/boards", tags=["boards"])


@router.get("", response_model=List[BoardSummary])
def list_boards(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT b.id, b.title, b.created_at,
               COUNT(c.id) as card_count
        FROM boards b
        LEFT JOIN columns col ON col.board_id = b.id
        LEFT JOIN cards c ON c.column_id = col.id
        WHERE b.user_id = ?
        GROUP BY b.id
        ORDER BY b.created_at ASC
        """,
        (current_user["sub"],),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        BoardSummary(id=r["id"], title=r["title"], created_at=r["created_at"], card_count=r["card_count"])
        for r in rows
    ]


@router.post("", response_model=BoardSummary, status_code=201)
def create_board(request: CreateBoardRequest, current_user: dict = Depends(get_current_user)):
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    board_id = f"board-{uuid.uuid4().hex[:12]}"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO boards (id, user_id, title) VALUES (?, ?, ?)",
        (board_id, current_user["sub"], request.title.strip()),
    )

    default_columns = [
        (f"col-{uuid.uuid4().hex[:8]}", board_id, "Backlog", 0),
        (f"col-{uuid.uuid4().hex[:8]}", board_id, "In Progress", 1),
        (f"col-{uuid.uuid4().hex[:8]}", board_id, "Done", 2),
    ]
    cursor.executemany(
        "INSERT INTO columns (id, board_id, title, [order]) VALUES (?, ?, ?, ?)",
        default_columns,
    )

    conn.commit()
    cursor.execute("SELECT id, title, created_at FROM boards WHERE id = ?", (board_id,))
    row = cursor.fetchone()
    conn.close()
    return BoardSummary(id=row["id"], title=row["title"], created_at=row["created_at"], card_count=0)


@router.get("/{board_id}", response_model=BoardData)
def get_board(board_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id FROM boards WHERE id = ? AND user_id = ?",
        (board_id, current_user["sub"]),
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Board not found")

    cursor.execute(
        "SELECT id, title, [order] FROM columns WHERE board_id = ? ORDER BY [order] ASC",
        (board_id,),
    )
    columns_rows = cursor.fetchall()

    columns = []
    cards_map = {}

    for row in columns_rows:
        col_id = row["id"]
        cursor.execute(
            "SELECT id, title, details, priority, due_date, labels FROM cards WHERE column_id = ? ORDER BY [order] ASC",
            (col_id,),
        )
        cards_rows = cursor.fetchall()
        card_ids = []
        for c_row in cards_rows:
            card_id = c_row["id"]
            card_ids.append(card_id)
            cards_map[card_id] = CardModel(
                id=card_id,
                title=c_row["title"],
                details=c_row["details"],
                priority=c_row["priority"],
                due_date=c_row["due_date"],
                labels=c_row["labels"],
            )
        columns.append(ColumnModel(id=col_id, title=row["title"], cardIds=card_ids))

    conn.close()
    return BoardData(columns=columns, cards=cards_map)


@router.put("/{board_id}")
def update_board(board_id: str, request: UpdateBoardRequest, current_user: dict = Depends(get_current_user)):
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE boards SET title = ? WHERE id = ? AND user_id = ?",
        (request.title.strip(), board_id, current_user["sub"]),
    )
    if cursor.rowcount == 0:
        conn.close()
        raise HTTPException(status_code=404, detail="Board not found")
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.delete("/{board_id}", status_code=204)
def delete_board(board_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM boards WHERE id = ? AND user_id = ?",
        (board_id, current_user["sub"]),
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Board not found")

    cursor.execute("DELETE FROM boards WHERE id = ?", (board_id,))
    conn.commit()
    conn.close()
