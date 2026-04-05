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
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS boards (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            title TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS columns (
            id TEXT PRIMARY KEY,
            board_id TEXT NOT NULL,
            title TEXT NOT NULL,
            [order] INTEGER NOT NULL DEFAULT 0,
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
            FOREIGN KEY(column_id) REFERENCES columns(id) ON DELETE CASCADE
        )
    """)

    conn.commit()

    # Run migrations to add new columns to existing tables
    _migrate(conn)

    seed_data(conn)
    conn.close()


def _migrate(conn):
    """Add new columns to existing tables if they don't exist (idempotent)."""
    cursor = conn.cursor()

    # users: add password_hash if missing
    cursor.execute("PRAGMA table_info(users)")
    user_cols = {row["name"] for row in cursor.fetchall()}
    if "password_hash" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")
    if "created_at" not in user_cols:
        cursor.execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT (datetime('now'))")

    # boards: add created_at if missing
    cursor.execute("PRAGMA table_info(boards)")
    board_cols = {row["name"] for row in cursor.fetchall()}
    if "created_at" not in board_cols:
        cursor.execute("ALTER TABLE boards ADD COLUMN created_at TEXT DEFAULT (datetime('now'))")

    # cards: add priority, due_date, labels if missing
    cursor.execute("PRAGMA table_info(cards)")
    card_cols = {row["name"] for row in cursor.fetchall()}
    if "priority" not in card_cols:
        cursor.execute("ALTER TABLE cards ADD COLUMN priority TEXT DEFAULT 'medium'")
    if "due_date" not in card_cols:
        cursor.execute("ALTER TABLE cards ADD COLUMN due_date TEXT")
    if "labels" not in card_cols:
        cursor.execute("ALTER TABLE cards ADD COLUMN labels TEXT DEFAULT ''")

    conn.commit()


def seed_data(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = 'user'")
    if cursor.fetchone():
        return

    # Seed the default user with hashed password
    cursor.execute(
        "INSERT OR IGNORE INTO users (id, username, password_hash) VALUES (?, ?, ?)",
        ("user-1", "user", hash_password("password")),
    )
    cursor.execute(
        "INSERT OR IGNORE INTO boards (id, user_id, title) VALUES (?, ?, ?)",
        ("board-1", "user-1", "MVP Board"),
    )

    columns = [
        ("col-backlog", "board-1", "Backlog", 0),
        ("col-discovery", "board-1", "Discovery", 1),
        ("col-progress", "board-1", "In Progress", 2),
        ("col-review", "board-1", "Review", 3),
        ("col-done", "board-1", "Done", 4),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO columns (id, board_id, title, [order]) VALUES (?, ?, ?, ?)",
        columns,
    )

    cards = [
        ("card-1", "col-backlog", "Align roadmap themes", "Draft quarterly themes with impact statements and metrics.", 0, "medium", None, ""),
        ("card-2", "col-backlog", "Gather customer signals", "Review support tags, sales notes, and churn feedback.", 1, "high", None, "research"),
        ("card-3", "col-discovery", "Prototype analytics view", "Sketch initial dashboard layout and key drill-downs.", 0, "medium", None, "design"),
        ("card-4", "col-progress", "Refine status language", "Standardize column labels and tone across the board.", 0, "low", None, ""),
        ("card-5", "col-progress", "Design card layout", "Add hierarchy and spacing for scanning dense lists.", 1, "medium", None, "design"),
        ("card-6", "col-review", "QA micro-interactions", "Verify hover, focus, and loading states.", 0, "high", None, "qa"),
        ("card-7", "col-done", "Ship marketing page", "Final copy approved and asset pack delivered.", 0, "medium", None, ""),
        ("card-8", "col-done", "Close onboarding sprint", "Document release notes and share internally.", 1, "low", None, ""),
    ]
    cursor.executemany(
        "INSERT OR IGNORE INTO cards (id, column_id, title, details, [order], priority, due_date, labels) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        cards,
    )
    conn.commit()
