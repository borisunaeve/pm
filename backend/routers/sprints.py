import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import (
    Sprint,
    CreateSprintRequest,
    UpdateSprintRequest,
)

router = APIRouter(tags=["sprints"])

VALID_STATUSES = {"planning", "active", "completed"}


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _assert_board_access(cursor, board_id: str, user_id: str):
    cursor.execute(
        """SELECT id FROM boards WHERE id = ? AND (
            user_id = ? OR id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (board_id, user_id, user_id),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Board not found")


def _assert_board_owner(cursor, board_id: str, user_id: str):
    cursor.execute("SELECT id FROM boards WHERE id = ? AND user_id = ?", (board_id, user_id))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Board not found")


def _get_sprint(cursor, sprint_id: str) -> dict:
    cursor.execute(
        """SELECT s.*,
               COUNT(c.id) as card_count,
               SUM(CASE WHEN col.title LIKE '%done%' OR col.title LIKE '%complete%' THEN 1 ELSE 0 END) as done_count
           FROM sprints s
           LEFT JOIN cards c ON c.sprint_id = s.id AND c.archived = 0
           LEFT JOIN columns col ON col.id = c.column_id
           WHERE s.id = ?
           GROUP BY s.id""",
        (sprint_id,),
    )
    row = cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Sprint not found")
    return row


def _row_to_sprint(row) -> Sprint:
    return Sprint(
        id=row["id"],
        board_id=row["board_id"],
        title=row["title"],
        goal=row["goal"] or "",
        start_date=row["start_date"],
        end_date=row["end_date"],
        status=row["status"],
        created_at=row["created_at"],
        card_count=row["card_count"] or 0,
        done_count=row["done_count"] or 0,
    )


# ── Board-scoped endpoints ─────────────────────────────────────────────────────

@router.get("/api/boards/{board_id}/sprints", response_model=List[Sprint])
def list_sprints(board_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_board_access(cursor, board_id, current_user["sub"])

    cursor.execute(
        """SELECT s.*,
               COUNT(c.id) as card_count,
               SUM(CASE WHEN col.title LIKE '%done%' OR col.title LIKE '%complete%' THEN 1 ELSE 0 END) as done_count
           FROM sprints s
           LEFT JOIN cards c ON c.sprint_id = s.id AND c.archived = 0
           LEFT JOIN columns col ON col.id = c.column_id
           WHERE s.board_id = ?
           GROUP BY s.id
           ORDER BY s.created_at ASC""",
        (board_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [_row_to_sprint(r) for r in rows]


@router.post("/api/boards/{board_id}/sprints", response_model=Sprint, status_code=201)
def create_sprint(
    board_id: str,
    request: CreateSprintRequest,
    current_user: dict = Depends(get_current_user),
):
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_board_access(cursor, board_id, current_user["sub"])

    sprint_id = f"sprint-{uuid.uuid4().hex[:10]}"
    cursor.execute(
        """INSERT INTO sprints (id, board_id, title, goal, start_date, end_date)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (sprint_id, board_id, request.title.strip(), request.goal or "",
         request.start_date, request.end_date),
    )
    conn.commit()
    row = _get_sprint(cursor, sprint_id)
    conn.close()
    return _row_to_sprint(row)


# ── Sprint-scoped endpoints ────────────────────────────────────────────────────

@router.get("/api/sprints/{sprint_id}", response_model=Sprint)
def get_sprint(sprint_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    row = _get_sprint(cursor, sprint_id)
    _assert_board_access(cursor, row["board_id"], current_user["sub"])
    conn.close()
    return _row_to_sprint(row)


@router.put("/api/sprints/{sprint_id}", response_model=Sprint)
def update_sprint(
    sprint_id: str,
    request: UpdateSprintRequest,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    row = _get_sprint(cursor, sprint_id)
    _assert_board_access(cursor, row["board_id"], current_user["sub"])

    updates, params = [], []
    if request.title is not None:
        if not request.title.strip():
            raise HTTPException(status_code=400, detail="Title cannot be empty")
        updates.append("title = ?"); params.append(request.title.strip())
    if request.goal is not None:
        updates.append("goal = ?"); params.append(request.goal)
    if request.start_date is not None:
        updates.append("start_date = ?"); params.append(request.start_date)
    if request.end_date is not None:
        updates.append("end_date = ?"); params.append(request.end_date)

    if updates:
        params.append(sprint_id)
        cursor.execute(f"UPDATE sprints SET {', '.join(updates)} WHERE id = ?", tuple(params))
        conn.commit()

    row = _get_sprint(cursor, sprint_id)
    conn.close()
    return _row_to_sprint(row)


@router.delete("/api/sprints/{sprint_id}", status_code=204)
def delete_sprint(sprint_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    row = _get_sprint(cursor, sprint_id)
    _assert_board_access(cursor, row["board_id"], current_user["sub"])

    # Unlink cards before deleting (FK is SET NULL but be explicit)
    cursor.execute("UPDATE cards SET sprint_id = NULL WHERE sprint_id = ?", (sprint_id,))
    cursor.execute("DELETE FROM sprints WHERE id = ?", (sprint_id,))
    conn.commit()
    conn.close()


@router.post("/api/sprints/{sprint_id}/start", response_model=Sprint)
def start_sprint(sprint_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    row = _get_sprint(cursor, sprint_id)
    _assert_board_access(cursor, row["board_id"], current_user["sub"])

    if row["status"] != "planning":
        raise HTTPException(status_code=400, detail="Only planning sprints can be started")

    # Only one active sprint per board
    cursor.execute(
        "SELECT id FROM sprints WHERE board_id = ? AND status = 'active'",
        (row["board_id"],),
    )
    if cursor.fetchone():
        raise HTTPException(status_code=409, detail="A sprint is already active on this board")

    cursor.execute("UPDATE sprints SET status = 'active' WHERE id = ?", (sprint_id,))
    conn.commit()
    row = _get_sprint(cursor, sprint_id)
    conn.close()
    return _row_to_sprint(row)


@router.post("/api/sprints/{sprint_id}/complete", response_model=Sprint)
def complete_sprint(sprint_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    row = _get_sprint(cursor, sprint_id)
    _assert_board_access(cursor, row["board_id"], current_user["sub"])

    if row["status"] != "active":
        raise HTTPException(status_code=400, detail="Only active sprints can be completed")

    cursor.execute("UPDATE sprints SET status = 'completed' WHERE id = ?", (sprint_id,))
    conn.commit()
    row = _get_sprint(cursor, sprint_id)
    conn.close()
    return _row_to_sprint(row)
