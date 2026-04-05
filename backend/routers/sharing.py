from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import BoardMember, ShareBoardRequest

router = APIRouter(prefix="/api/boards", tags=["sharing"])


def _assert_owner(cursor, board_id: str, user_id: str):
    cursor.execute("SELECT id FROM boards WHERE id = ? AND user_id = ?", (board_id, user_id))
    if not cursor.fetchone():
        raise HTTPException(status_code=403, detail="Only the board owner can manage sharing")


@router.get("/{board_id}/members", response_model=List[BoardMember])
def list_members(board_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Must be owner or member to view
    cursor.execute(
        """SELECT id FROM boards WHERE id = ? AND (
            user_id = ? OR
            id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (board_id, current_user["sub"], current_user["sub"]),
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Board not found")

    cursor.execute(
        """SELECT bm.user_id, u.username, bm.role, bm.added_at
           FROM board_members bm JOIN users u ON u.id = bm.user_id
           WHERE bm.board_id = ? ORDER BY bm.added_at ASC""",
        (board_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [BoardMember(user_id=r["user_id"], username=r["username"],
                        role=r["role"], added_at=r["added_at"]) for r in rows]


@router.post("/{board_id}/members", status_code=201)
def add_member(
    board_id: str,
    request: ShareBoardRequest,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_owner(cursor, board_id, current_user["sub"])

    cursor.execute("SELECT id FROM users WHERE username = ?", (request.username,))
    target = cursor.fetchone()
    if not target:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    if target["id"] == current_user["sub"]:
        conn.close()
        raise HTTPException(status_code=400, detail="Cannot share with yourself")

    cursor.execute(
        "INSERT OR IGNORE INTO board_members (board_id, user_id, role) VALUES (?, ?, 'member')",
        (board_id, target["id"]),
    )
    conn.commit()
    conn.close()
    return {"status": "success", "user_id": target["id"], "username": request.username}


@router.delete("/{board_id}/members/{user_id}", status_code=204)
def remove_member(
    board_id: str,
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_owner(cursor, board_id, current_user["sub"])
    cursor.execute(
        "DELETE FROM board_members WHERE board_id = ? AND user_id = ?",
        (board_id, user_id),
    )
    conn.commit()
    conn.close()
