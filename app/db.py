"""Persistent SQLite storage for chat sessions and message history."""
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

# Database path in project data folder
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "chat_history.db"


def get_db_connection() -> sqlite3.Connection:
    """Create and return a database connection with dict-like row access."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables for sessions and messages."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Sessions table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Messages table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            )
        """)

        # Index for fast retrieval by session_id
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages (session_id)
        """)
        conn.commit()


# Ensure tables are created on import
init_db()


def save_message(session_id: str, role: str, content: str) -> None:
    """Save a single message and update session metadata."""
    now_iso = datetime.utcnow().isoformat()

    with get_db_connection() as conn:
        cursor = conn.cursor()

        # Check if session exists
        cursor.execute("SELECT id FROM sessions WHERE id = ?", (session_id,))
        row = cursor.fetchone()

        if row is None:
            # Generate title from first user message (up to 40 characters)
            first_line = content.strip().split("\n")[0]
            title = (first_line[:37] + "...") if len(first_line) > 37 else first_line
            if not title:
                title = f"Chat {session_id[:8]}"

            cursor.execute(
                "INSERT INTO sessions (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
                (session_id, title, now_iso, now_iso),
            )
        else:
            cursor.execute(
                "UPDATE sessions SET updated_at = ? WHERE id = ?",
                (now_iso, session_id),
            )

        # Insert message
        cursor.execute(
            "INSERT INTO messages (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
            (session_id, role, content, now_iso),
        )
        conn.commit()


def get_messages(session_id: str) -> List[Dict]:
    """Retrieve all messages for a session ordered by timestamp."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, timestamp FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,),
        )
        rows = cursor.fetchall()
        return [
            {"role": row["role"], "content": row["content"], "timestamp": row["timestamp"]}
            for row in rows
        ]


def get_all_sessions() -> List[Dict]:
    """Retrieve all sessions ordered by most recently updated."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                s.id, 
                s.title, 
                s.created_at, 
                s.updated_at,
                COUNT(m.id) as message_count
            FROM sessions s
            LEFT JOIN messages m ON s.id = m.session_id
            GROUP BY s.id
            ORDER BY s.updated_at DESC
        """)
        rows = cursor.fetchall()
        return [
            {
                "session_id": row["id"],
                "title": row["title"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "message_count": row["message_count"],
            }
            for row in rows
        ]


def delete_session(session_id: str) -> bool:
    """Delete a session and all its messages."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()
        return cursor.rowcount > 0
