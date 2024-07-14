<<<<<<< HEAD
=======
# tests/test_database.py
import os
>>>>>>> Aronchick_PR_004_auto_save_state
import sqlite3
from unittest.mock import MagicMock, patch

import pytest

<<<<<<< HEAD
=======
# Set testing environment variable before importing database
os.environ["TESTING"] = "true"

>>>>>>> Aronchick_PR_004_auto_save_state
import database
from database import (
    ensure_table_exists,
    execute_transaction,
<<<<<<< HEAD
    get_total_tokens,
    init_db,
    load_state,
    save_state,
    save_total_tokens,
)


def test_get_db_connection():
    with database.get_db_connection() as conn:
        assert isinstance(conn, sqlite3.Connection)


def test_get_db_cursor():
    with database.get_db_connection() as conn:
        with database.get_db_cursor(conn) as cursor:
            assert isinstance(cursor, sqlite3.Cursor)
=======
    init_db,
    load_state,
    save_state,
)


@pytest.fixture(autouse=True)
def use_in_memory_database():
    print("\nSetting up in-memory database")
    original_db_file = database.DB_FILE
    database.DB_FILE = ":memory:"
    database.close_db_connection()  # Close any existing connection
    database.conversation_history = []  # Reset conversation_history
    database.init_db()  # Ensure tables are created for each test
    yield
    database.close_db_connection()  # Close the connection after the test
    database.conversation_history = []  # Reset conversation_history after test
    database.DB_FILE = original_db_file
>>>>>>> Aronchick_PR_004_auto_save_state


def test_execute_transaction():
    queries = [
        ("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)", ()),
        ("INSERT INTO test (value) VALUES (?)", ("test_value",)),
        ("SELECT value FROM test", ()),
    ]
    result = execute_transaction(queries)

    assert result == [[], [], [("test_value",)]]


def test_ensure_table_exists():
<<<<<<< HEAD
    result_conv = ensure_table_exists("conversation_history")
    result_token = ensure_table_exists("token_count")

    print(f"Result of creating conversation_history: {result_conv}")
    print(f"Result of creating token_count: {result_token}")

    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]  # Extract table names
        print(f"Tables found in the database: {tables}")

        # Check if tables exist
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_history'"
        )
        conv_exists = cursor.fetchone() is not None
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='token_count'"
        )
        token_exists = cursor.fetchone() is not None

        print(f"conversation_history exists: {conv_exists}")
        print(f"token_count exists: {token_exists}")

        assert (
            "conversation_history" in tables
        ), f"conversation_history not found in {tables}"
        assert "token_count" in tables, f"token_count not found in {tables}"
=======
    result = ensure_table_exists("conversation_history")
    assert result == [[]]

    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_history'"
        )
        assert cursor.fetchone() is not None
>>>>>>> Aronchick_PR_004_auto_save_state


def test_init_db():
    init_db()

    with database.get_db_connection() as conn:
        cursor = conn.cursor()
<<<<<<< HEAD
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        assert ("conversation_history",) in tables
        assert ("token_count",) in tables


def test_load_state():
    # First, ensure the table exists
    ensure_table_exists("conversation_history")

    # Insert test data
=======
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_history'"
        )
        assert cursor.fetchone() is not None


def test_load_state():
    ensure_table_exists("conversation_history")
>>>>>>> Aronchick_PR_004_auto_save_state
    execute_transaction(
        [
            (
                "INSERT INTO conversation_history (role, content) VALUES (?, ?)",
                ("user", "Hello"),
            ),
            (
                "INSERT INTO conversation_history (role, content) VALUES (?, ?)",
                ("assistant", "Hi there!"),
            ),
        ]
    )

<<<<<<< HEAD
    # Print the contents of the table for debugging
    result = execute_transaction([("SELECT * FROM conversation_history", ())])
    print(f"Contents of conversation_history table: {result}")

    # Load the state
    loaded_history = load_state()

    # Check the loaded history
    print(f"Loaded history: {loaded_history}")

    # Assert the loaded history matches what we expect
=======
    loaded_history = load_state()
>>>>>>> Aronchick_PR_004_auto_save_state
    assert loaded_history == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
<<<<<<< HEAD

    # Also check the global conversation_history variable
    print(f"Global conversation_history: {database.conversation_history}")
    assert database.conversation_history == [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]


def test_get_total_tokens():
    execute_transaction(
        [("INSERT INTO token_count (id, total_tokens) VALUES (1, 100)", ())]
    )

    assert get_total_tokens() == 100


def test_get_total_tokens_empty():
    assert get_total_tokens() == 0


def test_save_total_tokens():
    save_total_tokens(200)

    result = execute_transaction(
        [("SELECT total_tokens FROM token_count WHERE id = 1", ())]
    )
    assert result == [[(200,)]]
=======
    assert database.conversation_history == loaded_history
>>>>>>> Aronchick_PR_004_auto_save_state


def test_save_state():
    database.conversation_history = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]

    save_state()

    result = execute_transaction(
        [("SELECT role, content FROM conversation_history", ())]
    )
    assert result == [[("user", "Hello"), ("assistant", "Hi there!")]]


<<<<<<< HEAD
def test_save_state_empty():
    database.conversation_history = []

    save_state()

    result = execute_transaction(
        [("SELECT role, content FROM conversation_history", ())]
    )
    assert result == [[]]


=======
>>>>>>> Aronchick_PR_004_auto_save_state
@patch("database.get_db_connection")
def test_connection_closed_after_exception(mock_get_conn):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value = mock_cursor
    mock_get_conn.return_value.__enter__.return_value = mock_conn
    mock_cursor.execute.side_effect = sqlite3.Error("Test error")

    with pytest.raises(sqlite3.Error):
        execute_transaction([("SELECT * FROM non_existent_table", ())])

    # For in-memory databases, we don't close the connection after each transaction
    # Instead, we check if close_db_connection was called in the fixture teardown
    if database.DB_FILE == ":memory:":
        mock_conn.close.assert_not_called()
    else:
        mock_conn.close.assert_called_once()
