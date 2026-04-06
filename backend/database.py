import sqlite3
import os

from backend.auth import hash_password

DB_FILE = os.environ.get(
    "DB_FILE",
    os.path.join(os.path.dirname(__file__), "..", "data", "pm.db"),
)

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    db_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS boards (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            color TEXT DEFAULT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS board_members (
            board_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            added_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (board_id, user_id),
            FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS columns (
            id TEXT PRIMARY KEY,
            board_id TEXT NOT NULL,
            title TEXT NOT NULL,
            [order] INTEGER NOT NULL DEFAULT 0,
            wip_limit INTEGER,
            FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            column_id TEXT NOT NULL,
            title TEXT NOT NULL,
            details TEXT DEFAULT '',
            [order] INTEGER NOT NULL DEFAULT 0,
            priority TEXT DEFAULT 'medium',
            due_date TEXT,
            labels TEXT DEFAULT '',
            assignee_id TEXT,
            archived INTEGER NOT NULL DEFAULT 0,
            estimated_hours REAL,
            actual_hours REAL,
            sprint_id TEXT,
            FOREIGN KEY(column_id) REFERENCES columns(id) ON DELETE CASCADE,
            FOREIGN KEY(assignee_id) REFERENCES users(id) ON DELETE SET NULL,
            FOREIGN KEY(sprint_id) REFERENCES sprints(id) ON DELETE SET NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id TEXT NOT NULL,
            related_card_id TEXT NOT NULL,
            relation_type TEXT NOT NULL DEFAULT 'relates-to',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(card_id, related_card_id, relation_type),
            FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
            FOREIGN KEY(related_card_id) REFERENCES cards(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sprints (
            id TEXT PRIMARY KEY,
            board_id TEXT NOT NULL,
            title TEXT NOT NULL,
            goal TEXT DEFAULT '',
            start_date TEXT,
            end_date TEXT,
            status TEXT NOT NULL DEFAULT 'planning',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_comments (
            id TEXT PRIMARY KEY,
            card_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS checklist_items (
            id TEXT PRIMARY KEY,
            card_id TEXT NOT NULL,
            title TEXT NOT NULL,
            checked INTEGER NOT NULL DEFAULT 0,
            [order] INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS board_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_title TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_activity (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id   TEXT NOT NULL,
            user_id   TEXT NOT NULL,
            field     TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_watchers (
            card_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (card_id, user_id),
            FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            board_id TEXT,
            card_id TEXT,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE,
            FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE SET NULL
        )
    """)

    conn.commit()
    _migrate(conn)
    seed_data(conn)
    conn.close()


def _migrate(conn):
    """Add new columns to existing tables if they don't exist (idempotent)."""
    cursor = conn.cursor()

    # users
    cursor.execute("PRAGMA table_info(users)")
    user_cols = {row["name"] for row in cursor.fetchall()}
    if "password_hash" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")
    if "created_at" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT ''")
    if "display_name" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN display_name TEXT DEFAULT ''")

    # boards
    cursor.execute("PRAGMA table_info(boards)")
    board_cols = {row["name"] for row in cursor.fetchall()}
    if "created_at" not in board_cols:
        cursor.execute("ALTER TABLE boards ADD COLUMN created_at TEXT DEFAULT ''")
    if "description" not in board_cols:
        cursor.execute("ALTER TABLE boards ADD COLUMN description TEXT DEFAULT ''")
    if "color" not in board_cols:
        cursor.execute("ALTER TABLE boards ADD COLUMN color TEXT DEFAULT NULL")

    # columns
    cursor.execute("PRAGMA table_info(columns)")
    col_cols = {row["name"] for row in cursor.fetchall()}
    if "wip_limit" not in col_cols:
        cursor.execute("ALTER TABLE columns ADD COLUMN wip_limit INTEGER")

    # cards
    cursor.execute("PRAGMA table_info(cards)")
    card_cols = {row["name"] for row in cursor.fetchall()}
    if "priority" not in card_cols:
        cursor.execute("ALTER TABLE cards ADD COLUMN priority TEXT DEFAULT 'medium'")
    if "due_date" not in card_cols:
        cursor.execute("ALTER TABLE cards ADD COLUMN due_date TEXT")
    if "labels" not in card_cols:
        cursor.execute("ALTER TABLE cards ADD COLUMN labels TEXT DEFAULT ''")
    if "assignee_id" not in card_cols:
        cursor.execute("ALTER TABLE cards ADD COLUMN assignee_id TEXT REFERENCES users(id) ON DELETE SET NULL")
    if "archived" not in card_cols:
        cursor.execute("ALTER TABLE cards ADD COLUMN archived INTEGER NOT NULL DEFAULT 0")
    if "estimated_hours" not in card_cols:
        cursor.execute("ALTER TABLE cards ADD COLUMN estimated_hours REAL")
    if "actual_hours" not in card_cols:
        cursor.execute("ALTER TABLE cards ADD COLUMN actual_hours REAL")
    if "sprint_id" not in card_cols:
        cursor.execute("ALTER TABLE cards ADD COLUMN sprint_id TEXT REFERENCES sprints(id) ON DELETE SET NULL")

    # sprints table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sprints (
            id TEXT PRIMARY KEY,
            board_id TEXT NOT NULL,
            title TEXT NOT NULL,
            goal TEXT DEFAULT '',
            start_date TEXT,
            end_date TEXT,
            status TEXT NOT NULL DEFAULT 'planning',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE
        )
    """)

    # card_relations table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_relations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id TEXT NOT NULL,
            related_card_id TEXT NOT NULL,
            relation_type TEXT NOT NULL DEFAULT 'relates-to',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(card_id, related_card_id, relation_type),
            FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
            FOREIGN KEY(related_card_id) REFERENCES cards(id) ON DELETE CASCADE
        )
    """)

    # card_activity table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_activity (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            card_id   TEXT NOT NULL,
            user_id   TEXT NOT NULL,
            field     TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # card_watchers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS card_watchers (
            card_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            PRIMARY KEY (card_id, user_id),
            FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # user_notifications table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            board_id TEXT,
            card_id TEXT,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            read INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE,
            FOREIGN KEY(card_id) REFERENCES cards(id) ON DELETE SET NULL
        )
    """)

    conn.commit()


def seed_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id, password_hash FROM users WHERE username = 'user'")
    row = cursor.fetchone()
    if row:
        # Repair empty password_hash left by old migration
        if not row["password_hash"]:
            cursor.execute(
                "UPDATE users SET password_hash=? WHERE username='user'",
                (hash_password("password"),),
            )
            conn.commit()
        return

    cursor.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (?, ?, ?)",
        ("user-1", "user", hash_password("password")),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO boards (id, user_id, title) VALUES (?, ?, ?)",
        ("board-1", "user-1", "MVP Board"),
    )

    columns = [
        ("col-backlog",   "board-1", "Backlog",     0, None),
        ("col-discovery", "board-1", "Discovery",   1, None),
        ("col-progress",  "board-1", "In Progress", 2, 3),
        ("col-review",    "board-1", "Review",      3, 2),
        ("col-done",      "board-1", "Done",        4, None),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO columns (id, board_id, title, [order], wip_limit) VALUES (?, ?, ?, ?, ?)",
        columns,
    )

    cards = [
        ("card-1", "col-backlog",   "Align roadmap themes",    "Draft quarterly themes with impact statements and metrics.", 0, "medium", None, ""),
        ("card-2", "col-backlog",   "Gather customer signals",  "Review support tags, sales notes, and churn feedback.",      1, "high",   None, "research"),
        ("card-3", "col-discovery", "Prototype analytics view", "Sketch initial dashboard layout and key drill-downs.",       0, "medium", None, "design"),
        ("card-4", "col-progress",  "Refine status language",   "Standardize column labels and tone across the board.",       0, "low",    None, ""),
        ("card-5", "col-progress",  "Design card layout",       "Add hierarchy and spacing for scanning dense lists.",        1, "medium", None, "design"),
        ("card-6", "col-review",    "QA micro-interactions",    "Verify hover, focus, and loading states.",                   0, "high",   None, "qa"),
        ("card-7", "col-done",      "Ship marketing page",      "Final copy approved and asset pack delivered.",              0, "medium", None, ""),
        ("card-8", "col-done",      "Close onboarding sprint",  "Document release notes and share internally.",               1, "low",    None, ""),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO cards (id, column_id, title, details, [order], priority, due_date, labels) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        cards,
    )
    conn.commit()
