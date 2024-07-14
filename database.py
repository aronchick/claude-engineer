import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

from config import DB_FILE

conversation_history: List[Dict[str, Any]] = []

_connection = None


@contextmanager
def get_db_connection():
    global _connection
    if DB_FILE == ":memory:":
        if _connection is None:
            _connection = sqlite3.connect(DB_FILE)
        conn = _connection
    else:
        conn = sqlite3.connect(DB_FILE)

    try:
        yield conn
    finally:
        if DB_FILE != ":memory:":
            conn.close()


def close_db_connection():
    global _connection
    if _connection:
        _connection.close()
        _connection = None


@contextmanager
def get_db_cursor(conn):
    cursor = conn.cursor()
    try:
        yield cursor
    finally:
        cursor.close()


def execute_transaction(queries: List[Tuple[str, tuple]]) -> List[List[Tuple]]:
    results = []
    with get_db_connection() as conn:
        with get_db_cursor(conn) as cursor:
            for query, params in queries:
                cursor.execute(query, params)
                if query.strip().upper().startswith("SELECT"):
                    results.append(cursor.fetchall())
                else:
                    results.append([])
        conn.commit()
    return results


def ensure_table_exists(table_name: str) -> List[List[Tuple]]:
    if table_name == "conversation_history":
        return execute_transaction(
            [
                (
                    """
                CREATE TABLE IF NOT EXISTS conversation_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT
                )
                """,
                    (),
                ),
                # Add this line to ensure the metadata column exists
                ("PRAGMA table_info(conversation_history)", ()),
            ]
        )
    elif table_name == "token_count":
        return execute_transaction(
            [
                (
                    """
            CREATE TABLE IF NOT EXISTS token_count (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                total_tokens INTEGER
            )
            """,
                    (),
                )
            ]
        )
    else:
        raise ValueError(f"Unknown table name: {table_name}")


def init_db():
    ensure_table_exists("conversation_history")
    ensure_table_exists("token_count")

    # Add this block to check and add the metadata column if it doesn't exist
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(conversation_history)")
        columns = [column[1] for column in cursor.fetchall()]
        if "metadata" not in columns:
            cursor.execute("ALTER TABLE conversation_history ADD COLUMN metadata TEXT")
        conn.commit()


def get_total_tokens() -> int:
    ensure_table_exists("token_count")
    results = execute_transaction(
        [("SELECT total_tokens FROM token_count WHERE id = 1", ())]
    )
    return results[0][0][0] if results[0] else 0


def save_total_tokens(tokens: int):
    ensure_table_exists("token_count")
    execute_transaction(
        [
            (
                "INSERT OR REPLACE INTO token_count (id, total_tokens) VALUES (1, ?)",
                (tokens,),
            )
        ]
    )


def save_message(
    session_id: str, role: str, content: str, metadata: Dict[str, Any] = None
):
    ensure_table_exists("conversation_history")

    timestamp = datetime.now(timezone.utc).isoformat()
    metadata_json = json.dumps(metadata) if metadata else None

    execute_transaction(
        [
            (
                "INSERT INTO conversation_history (session_id, timestamp, role, content, metadata) VALUES (?, ?, ?, ?, ?)",
                (session_id, timestamp, role, content, metadata_json),
            )
        ]
    )


def load_state(session_id: str = None):
    global conversation_history
    ensure_table_exists("conversation_history")

    if session_id:
        results = execute_transaction(
            [
                (
                    "SELECT role, content, metadata FROM conversation_history WHERE session_id = ? ORDER BY timestamp",
                    (session_id,),
                )
            ]
        )
    else:
        results = execute_transaction(
            [
                (
                    "SELECT role, content, metadata FROM conversation_history ORDER BY timestamp",
                    (),
                )
            ]
        )

    conversation_history = [
        {
            "role": role,
            "content": content,
            "metadata": json.loads(metadata)
            if metadata and isinstance(metadata, str)
            else {},
        }
        for role, content, metadata in results[0]
    ]
    return conversation_history


def save_state():
    global conversation_history
    ensure_table_exists("conversation_history")

    session_id = str(uuid.uuid4())  # Generate a new session_id for this save operation
    timestamp = datetime.utcnow().isoformat()

    queries = [("DELETE FROM conversation_history", ())]
    queries.extend(
        [
            (
                "INSERT INTO conversation_history (session_id, timestamp, role, content, metadata) VALUES (?, ?, ?, ?, ?)",
                (
                    session_id,
                    timestamp,
                    entry["role"],
                    entry["content"],
                    json.dumps(entry.get("metadata", {})),
                ),
            )
            for entry in conversation_history
        ]
    )

    execute_transaction(queries)


def get_session_history(session_id: str):
    results = execute_transaction(
        [
            (
                "SELECT timestamp, role, content, metadata FROM conversation_history WHERE session_id = ? ORDER BY timestamp",
                (session_id,),
            )
        ]
    )
    return [
        {
            "timestamp": timestamp,
            "role": role,
            "content": content,
            "metadata": json.loads(metadata) if metadata else {},
        }
        for timestamp, role, content, metadata in results[0]
    ]


# Initialize the database
init_db()
