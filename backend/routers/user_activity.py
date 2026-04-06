from typing import List, Optional
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.auth import get_current_user
from backend.database import get_db_connection

router = APIRouter(prefix="/api/users/me", tags=["user_activity"])


class ActivityItem(BaseModel):
    id: int
    board_id: str
    board_title: str
    action: str
    entity_type: str
    entity_title: Optional[str] = None
    created_at: str


@router.get("/activity", response_model=List[ActivityItem])
def get_my_activity(
    limit: int = 50,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT ba.id, ba.board_id, b.title as board_title,
                  ba.action, ba.entity_type, ba.entity_title, ba.created_at
           FROM board_activity ba
           JOIN boards b ON b.id = ba.board_id
           WHERE ba.user_id = ?
           ORDER BY ba.created_at DESC
           LIMIT ?""",
        (current_user["sub"], limit),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        ActivityItem(
            id=r["id"],
            board_id=r["board_id"],
            board_title=r["board_title"],
            action=r["action"],
            entity_type=r["entity_type"],
            entity_title=r["entity_title"],
            created_at=r["created_at"],
        )
        for r in rows
    ]
