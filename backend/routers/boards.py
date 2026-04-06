import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from typing import List
from backend.models import ActivityEntry, BoardData, BoardSummary, CardModel, ColumnModel, CreateBoardRequest, UpdateBoardRequest

router = APIRouter(prefix="/api/boards", tags=["boards"])

# Board templates: list of (title, wip_limit) tuples
BOARD_TEMPLATES: dict[str, list[tuple[str, int | None]]] = {
    "software": [
        ("Backlog", None), ("In Progress", 3), ("In Review", 2),
        ("Testing", None), ("Done", None),
    ],
    "marketing": [
        ("Ideas", None), ("Planning", None), ("In Production", 2),
        ("Review", None), ("Published", None),
    ],
    "personal": [
        ("To Do", None), ("Doing", 3), ("Done", None),
    ],
}


def _assert_access(cursor, board_id: str, user_id: str):
    """Allow board owner OR member."""
    cursor.execute(
        """SELECT id FROM boards WHERE id = ? AND (
            user_id = ? OR
            id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (board_id, user_id, user_id),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Board not found")


def _assert_owner(cursor, board_id: str, user_id: str):
    cursor.execute("SELECT id FROM boards WHERE id = ? AND user_id = ?", (board_id, user_id))
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Board not found")


@router.get("", response_model=List[BoardSummary])
def list_boards(current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT b.id, b.title, b.created_at,
               COUNT(CASE WHEN c.archived = 0 THEN 1 END) as card_count
        FROM boards b
        LEFT JOIN columns col ON col.board_id = b.id
        LEFT JOIN cards c ON c.column_id = col.id
        WHERE b.user_id = ? OR b.id IN (SELECT board_id FROM board_members WHERE user_id = ?)
        GROUP BY b.id
        ORDER BY b.created_at ASC
        """,
        (current_user["sub"], current_user["sub"]),
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

    template_columns = BOARD_TEMPLATES.get(request.template or "", [])
    if template_columns:
        default_columns = [
            (f"col-{uuid.uuid4().hex[:8]}", board_id, title, idx, wip)
            for idx, (title, wip) in enumerate(template_columns)
        ]
    else:
        default_columns = [
            (f"col-{uuid.uuid4().hex[:8]}", board_id, "Backlog", 0, None),
            (f"col-{uuid.uuid4().hex[:8]}", board_id, "In Progress", 1, None),
            (f"col-{uuid.uuid4().hex[:8]}", board_id, "Done", 2, None),
        ]
    cursor.executemany(
        "INSERT INTO columns (id, board_id, title, [order], wip_limit) VALUES (?, ?, ?, ?, ?)",
        default_columns,
    )

    conn.commit()
    cursor.execute("SELECT id, title, created_at FROM boards WHERE id = ?", (board_id,))
    row = cursor.fetchone()
    conn.close()
    return BoardSummary(id=row["id"], title=row["title"], created_at=row["created_at"], card_count=0)


@router.get("/{board_id}", response_model=BoardData)
def get_board(
    board_id: str,
    include_archived: bool = False,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_access(cursor, board_id, current_user["sub"])

    cursor.execute(
        "SELECT id, title, [order], wip_limit FROM columns WHERE board_id = ? ORDER BY [order] ASC",
        (board_id,),
    )
    columns_rows = cursor.fetchall()

    columns = []
    cards_map = {}
    archived_map = {}

    archived_filter = "" if include_archived else "AND c.archived = 0"

    for row in columns_rows:
        col_id = row["id"]
        cursor.execute(
            f"""SELECT c.id, c.title, c.details, c.priority, c.due_date, c.labels,
                      c.assignee_id, u.username as assignee_username,
                      c.archived, c.estimated_hours, c.actual_hours,
                      c.sprint_id, s.title as sprint_title,
                      (SELECT COUNT(*) FROM checklist_items WHERE card_id = c.id) as checklist_total,
                      (SELECT COUNT(*) FROM checklist_items WHERE card_id = c.id AND checked = 1) as checklist_done
               FROM cards c
               LEFT JOIN users u ON u.id = c.assignee_id
               LEFT JOIN sprints s ON s.id = c.sprint_id
               WHERE c.column_id = ? {archived_filter} ORDER BY c.[order] ASC""",
            (col_id,),
        )
        cards_rows = cursor.fetchall()
        card_ids = []
        for c_row in cards_rows:
            card_id = c_row["id"]
            is_archived = bool(c_row["archived"])
            if not is_archived:
                card_ids.append(card_id)
            else:
                archived_map[card_id] = True
            cards_map[card_id] = CardModel(
                id=card_id,
                title=c_row["title"],
                details=c_row["details"],
                priority=c_row["priority"],
                due_date=c_row["due_date"],
                labels=c_row["labels"],
                checklist_total=c_row["checklist_total"],
                checklist_done=c_row["checklist_done"],
                assignee_id=c_row["assignee_id"],
                assignee_username=c_row["assignee_username"],
                archived=is_archived,
                estimated_hours=c_row["estimated_hours"],
                actual_hours=c_row["actual_hours"],
                sprint_id=c_row["sprint_id"],
                sprint_title=c_row["sprint_title"],
            )
        columns.append(ColumnModel(id=col_id, title=row["title"], cardIds=card_ids, wip_limit=row["wip_limit"]))

    conn.close()
    return BoardData(columns=columns, cards=cards_map)


@router.put("/{board_id}")
def update_board(board_id: str, request: UpdateBoardRequest, current_user: dict = Depends(get_current_user)):
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")

    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_owner(cursor, board_id, current_user["sub"])
    cursor.execute("UPDATE boards SET title = ? WHERE id = ?", (request.title.strip(), board_id))
    conn.commit()
    conn.close()
    return {"status": "success"}


@router.delete("/{board_id}", status_code=204)
def delete_board(board_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_owner(cursor, board_id, current_user["sub"])
    cursor.execute("DELETE FROM boards WHERE id = ?", (board_id,))
    conn.commit()
    conn.close()


@router.get("/{board_id}/activity", response_model=List[ActivityEntry])
def get_board_activity(
    board_id: str,
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_access(cursor, board_id, current_user["sub"])
    cursor.execute(
        """SELECT a.id, a.board_id, a.user_id, u.username, a.action,
                  a.entity_type, a.entity_title, a.created_at
           FROM board_activity a JOIN users u ON u.id = a.user_id
           WHERE a.board_id = ?
           ORDER BY a.created_at DESC LIMIT ?""",
        (board_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        ActivityEntry(
            id=r["id"], board_id=r["board_id"], user_id=r["user_id"],
            username=r["username"], action=r["action"], entity_type=r["entity_type"],
            entity_title=r["entity_title"], created_at=r["created_at"],
        )
        for r in rows
    ]
