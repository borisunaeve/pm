import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import CardModel, CreateSubtaskRequest

router = APIRouter(prefix="/api/cards", tags=["subtasks"])


def _assert_card_access(cursor, card_id: str, user_id: str):
    cursor.execute(
        """SELECT c.id, c.column_id, col.board_id FROM cards c
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


@router.get("/{card_id}/subtasks", response_model=List[CardModel])
def list_subtasks(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])

    cursor.execute(
        """SELECT c.id, c.title, c.details, c.priority, c.due_date, c.labels,
                  c.assignee_id, u.username as assignee_username,
                  c.archived, c.estimated_hours, c.actual_hours,
                  c.sprint_id, c.parent_card_id,
                  (SELECT COUNT(*) FROM checklist_items WHERE card_id = c.id) as checklist_total,
                  (SELECT COUNT(*) FROM checklist_items WHERE card_id = c.id AND checked = 1) as checklist_done,
                  (SELECT COUNT(*) FROM cards sub WHERE sub.parent_card_id = c.id) as subtask_count
           FROM cards c
           LEFT JOIN users u ON u.id = c.assignee_id
           WHERE c.parent_card_id = ? AND c.archived = 0
           ORDER BY c.[order] ASC""",
        (card_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        CardModel(
            id=r["id"], title=r["title"], details=r["details"],
            priority=r["priority"], due_date=r["due_date"], labels=r["labels"],
            checklist_total=r["checklist_total"], checklist_done=r["checklist_done"],
            assignee_id=r["assignee_id"], assignee_username=r["assignee_username"],
            archived=bool(r["archived"]), estimated_hours=r["estimated_hours"],
            actual_hours=r["actual_hours"], sprint_id=r["sprint_id"],
            parent_card_id=r["parent_card_id"], subtask_count=r["subtask_count"],
        )
        for r in rows
    ]


@router.post("/{card_id}/subtasks", response_model=CardModel, status_code=201)
def create_subtask(
    card_id: str,
    request: CreateSubtaskRequest,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    parent_row = _assert_card_access(cursor, card_id, current_user["sub"])

    new_id = f"card-{uuid.uuid4().hex[:8]}"
    # Subtask lives in the same column as the parent
    cursor.execute(
        "SELECT MAX([order]) as max_o FROM cards WHERE column_id = ?",
        (parent_row["column_id"],),
    )
    max_row = cursor.fetchone()
    next_order = (max_row["max_o"] + 1) if max_row["max_o"] is not None else 0

    cursor.execute(
        """INSERT INTO cards
           (id, column_id, title, details, [order], priority, due_date, labels,
            assignee_id, parent_card_id)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (new_id, parent_row["column_id"], request.title, request.details or "",
         next_order, request.priority or "medium", request.due_date, "",
         request.assignee_id, card_id),
    )

    # Auto-watch creator
    cursor.execute(
        "INSERT OR IGNORE INTO card_watchers (card_id, user_id) VALUES (?, ?)",
        (new_id, current_user["sub"]),
    )

    # Log board activity
    cursor.execute("SELECT board_id FROM columns WHERE id = ?", (parent_row["column_id"],))
    col_row = cursor.fetchone()
    if col_row:
        cursor.execute(
            "INSERT INTO board_activity (board_id, user_id, action, entity_type, entity_title) VALUES (?, ?, ?, ?, ?)",
            (col_row["board_id"], current_user["sub"], "created", "subtask", request.title),
        )

    conn.commit()
    conn.close()
    return CardModel(
        id=new_id, title=request.title, details=request.details or "",
        priority=request.priority or "medium", due_date=request.due_date,
        labels="", checklist_total=0, checklist_done=0,
        assignee_id=request.assignee_id, archived=False,
        parent_card_id=card_id, subtask_count=0,
    )
