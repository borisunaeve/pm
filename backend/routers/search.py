from typing import List

from fastapi import APIRouter, Depends, Query

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import SearchResultCard

router = APIRouter(prefix="/api/search", tags=["search"])


@router.get("", response_model=List[SearchResultCard])
def search_cards(
    q: str = Query(..., min_length=1),
    include_archived: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """Search cards by title or details across all boards the user can access."""
    conn = get_db_connection()
    cursor = conn.cursor()

    like = f"%{q}%"
    archived_filter = "" if include_archived else "AND c.archived = 0"

    cursor.execute(
        f"""SELECT c.id, c.title, c.details, c.priority, c.labels, c.archived,
                   b.id as board_id, b.title as board_title,
                   col.title as column_title
            FROM cards c
            JOIN columns col ON col.id = c.column_id
            JOIN boards b ON b.id = col.board_id
            WHERE (b.user_id = ? OR b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))
              AND (c.title LIKE ? OR c.details LIKE ?)
              {archived_filter}
            ORDER BY b.title ASC, c.title ASC
            LIMIT 50""",
        (current_user["sub"], current_user["sub"], like, like),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        SearchResultCard(
            id=r["id"],
            title=r["title"],
            details=r["details"],
            priority=r["priority"],
            labels=r["labels"],
            board_id=r["board_id"],
            board_title=r["board_title"],
            column_title=r["column_title"],
            archived=bool(r["archived"]),
        )
        for r in rows
    ]
