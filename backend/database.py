import sqlite3
import os

DB_FILE = os.environ.get("DB_FILE", "/app/data/pm.db")

def get_db_connection():
    # Helper to enforce WAL mode and row factory
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    db_dir = os.path.dirname(DB_FILE)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
        
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create Users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT UNIQUE
        )
    """)

    # Create Boards
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS boards (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            title TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    # Create Columns
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS columns (
            id TEXT PRIMARY KEY,
            board_id TEXT,
            title TEXT,
            [order] INTEGER,
            FOREIGN KEY(board_id) REFERENCES boards(id)
        )
    """)

    # Create Cards
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cards (
            id TEXT PRIMARY KEY,
            column_id TEXT,
            title TEXT,
            details TEXT,
            [order] INTEGER,
            FOREIGN KEY(column_id) REFERENCES columns(id)
        )
    """)

    conn.commit()
    seed_data(conn)
    conn.close()

def seed_data(conn):
    # Check if 'user' exists, otherwise seed MVP data
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE id = 'user-1'")
    if cursor.fetchone():
        return

    # Seed the user and board
    cursor.execute("INSERT INTO users (id, username) VALUES ('user-1', 'user')")
    cursor.execute("INSERT INTO boards (id, user_id, title) VALUES ('board-1', 'user-1', 'MVP Board')")

    # Seed initial columns based on kanban.ts
    columns = [
        ('col-backlog', 'board-1', 'Backlog', 0),
        ('col-discovery', 'board-1', 'Discovery', 1),
        ('col-progress', 'board-1', 'In Progress', 2),
        ('col-review', 'board-1', 'Review', 3),
        ('col-done', 'board-1', 'Done', 4),
    ]
    cursor.executemany("INSERT INTO columns (id, board_id, title, [order]) VALUES (?, ?, ?, ?)", columns)

    # Seed initial cards based on kanban.ts
    cards = [
        ('card-1', 'col-backlog', 'Align roadmap themes', 'Draft quarterly themes with impact statements and metrics.', 0),
        ('card-2', 'col-backlog', 'Gather customer signals', 'Review support tags, sales notes, and churn feedback.', 1),
        ('card-3', 'col-discovery', 'Prototype analytics view', 'Sketch initial dashboard layout and key drill-downs.', 0),
        ('card-4', 'col-progress', 'Refine status language', 'Standardize column labels and tone across the board.', 0),
        ('card-5', 'col-progress', 'Design card layout', 'Add hierarchy and spacing for scanning dense lists.', 1),
        ('card-6', 'col-review', 'QA micro-interactions', 'Verify hover, focus, and loading states.', 0),
        ('card-7', 'col-done', 'Ship marketing page', 'Final copy approved and asset pack delivered.', 0),
        ('card-8', 'col-done', 'Close onboarding sprint', 'Document release notes and share internally.', 1),
    ]
    cursor.executemany("INSERT INTO cards (id, column_id, title, details, [order]) VALUES (?, ?, ?, ?, ?)", cards)
    conn.commit()
