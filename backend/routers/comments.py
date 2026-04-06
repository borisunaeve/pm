import re
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.database import get_db_connection
from backend.models import Comment, CreateCommentRequest
from backend.notify import notify_watchers

router = APIRouter(prefix="/api/cards", tags=["comments"])

_MENTION_RE = re.compile(r"@(\w+)")


def _assert_card_access(cursor, card_id: str, user_id: str):
    cursor.execute(
        """SELECT c.id FROM cards c
           JOIN columns col ON col.id = c.column_id
           JOIN boards b ON b.id = col.board_id
           WHERE c.id = ? AND (b.user_id = ? OR
               b.id IN (SELECT board_id FROM board_members WHERE user_id = ?))""",
        (card_id, user_id, user_id),
    )
    if not cursor.fetchone():
        raise HTTPException(status_code=404, detail="Card not found")


def _process_mentions(cursor, content: str, card_id: str, board_id: str,
                      actor_id: str, card_title: str):
    """Parse @mentions in content, send notifications to mentioned board members."""
    usernames = set(_MENTION_RE.findall(content))
    for username in usernames:
        cursor.execute(
            """SELECT u.id FROM users u
               JOIN board_members bm ON bm.user_id = u.id
               WHERE u.username = ? AND bm.board_id = ?
               UNION
               SELECT u.id FROM users u
               JOIN boards b ON b.user_id = u.id
               WHERE u.username = ? AND b.id = ?""",
            (username, board_id, username, board_id),
        )
        row = cursor.fetchone()
        if row and row["id"] != actor_id:
            mentioned_id = row["id"]
            cursor.execute("SELECT username FROM users WHERE id = ?", (actor_id,))
            actor_row = cursor.fetchone()
            actor_name = actor_row["username"] if actor_row else "Someone"
            # Auto-watch the mentioned user
            cursor.execute(
                "INSERT OR IGNORE INTO card_watchers (card_id, user_id) VALUES (?, ?)",
                (card_id, mentioned_id),
            )
            cursor.execute(
                """INSERT INTO user_notifications (user_id, board_id, card_id, type, message)
                   VALUES (?, ?, ?, ?, ?)""",
                (mentioned_id, board_id, card_id, "mentioned",
                 f"{actor_name} mentioned you in \"{card_title}\""),
            )


@router.get("/{card_id}/comments", response_model=List[Comment])
def list_comments(card_id: str, current_user: dict = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])

    cursor.execute(
        """SELECT cc.id, cc.card_id, cc.user_id, u.username,
                  COALESCE(u.display_name, '') as display_name,
                  cc.content, cc.created_at
           FROM card_comments cc JOIN users u ON u.id = cc.user_id
           WHERE cc.card_id = ? ORDER BY cc.created_at ASC""",
        (card_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        Comment(
            id=r["id"], card_id=r["card_id"], user_id=r["user_id"],
            username=r["username"], display_name=r["display_name"] or "",
            content=r["content"], created_at=r["created_at"],
        )
        for r in rows
    ]


@router.post("/{card_id}/comments", response_model=Comment, status_code=201)
def create_comment(
    card_id: str,
    request: CreateCommentRequest,
    current_user: dict = Depends(get_current_user),
):
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Comment cannot be empty")

    conn = get_db_connection()
    cursor = conn.cursor()
    _assert_card_access(cursor, card_id, current_user["sub"])

    comment_id = f"comment-{uuid.uuid4().hex[:12]}"
    cursor.execute(
        "INSERT INTO card_comments (id, card_id, user_id, content) VALUES (?, ?, ?, ?)",
        (comment_id, card_id, current_user["sub"], request.content.strip()),
    )

    # Get card/actor info for notifications
    cursor.execute(
        """SELECT c.title, col.board_id FROM cards c
           JOIN columns col ON col.id = c.column_id WHERE c.id = ?""",
        (card_id,),
    )
    card_row = cursor.fetchone()
    cursor.execute("SELECT username FROM users WHERE id = ?", (current_user["sub"],))
    actor_row = cursor.fetchone()

    if card_row and actor_row:
        # Notify watchers
        notify_watchers(
            cursor, card_id, current_user["sub"],
            "comment_added",
            f"{actor_row['username']} commented on \"{card_row['title']}\"",
            board_id=card_row["board_id"],
        )
        # Process @mentions
        _process_mentions(
            cursor, request.content.strip(), card_id,
            card_row["board_id"], current_user["sub"], card_row["title"],
        )

    conn.commit()

    cursor.execute(
        """SELECT cc.id, cc.card_id, cc.user_id, u.username,
                  COALESCE(u.display_name, '') as display_name,
                  cc.content, cc.created_at
           FROM card_comments cc JOIN users u ON u.id = cc.user_id WHERE cc.id = ?""",
        (comment_id,),
    )
    row = cursor.fetchone()
    conn.close()
    return Comment(
        id=row["id"], card_id=row["card_id"], user_id=row["user_id"],
        username=row["username"], display_name=row["display_name"] or "",
        content=row["content"], created_at=row["created_at"],
    )


@router.delete("/{card_id}/comments/{comment_id}", status_code=204)
def delete_comment(
    card_id: str,
    comment_id: str,
    current_user: dict = Depends(get_current_user),
):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id FROM card_comments WHERE id = ? AND card_id = ? AND user_id = ?",
        (comment_id, card_id, current_user["sub"]),
    )
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Comment not found")
    cursor.execute("DELETE FROM card_comments WHERE id = ?", (comment_id,))
    conn.commit()
    conn.close()
