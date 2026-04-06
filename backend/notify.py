"""Shared helper for creating persistent notifications for card watchers."""


def notify_watchers(cursor, card_id: str, actor_id: str, ntype: str, message: str,
                    board_id: str | None = None):
    """Insert a user_notification row for each watcher of card_id, except the actor."""
    cursor.execute(
        "SELECT user_id FROM card_watchers WHERE card_id = ? AND user_id != ?",
        (card_id, actor_id),
    )
    watcher_ids = [r["user_id"] for r in cursor.fetchall()]
    for uid in watcher_ids:
        cursor.execute(
            """INSERT INTO user_notifications (user_id, board_id, card_id, type, message)
               VALUES (?, ?, ?, ?, ?)""",
            (uid, board_id, card_id, ntype, message),
        )
