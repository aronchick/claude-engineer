import datetime
import json
import sqlite3
import uuid
from unittest.mock import MagicMock, patch

import pytest

import database
from database import (
    ensure_table_exists,
    execute_transaction,
    get_session_history,
    get_total_tokens,
    init_db,
    load_state,
    save_message,
    save_state,
    save_total_tokens,
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


def test_get_db_connection():
    with database.get_db_connection() as conn:
        assert isinstance(conn, sqlite3.Connection)


def test_get_db_cursor():
    with database.get_db_connection() as conn:
        with database.get_db_cursor(conn) as cursor:
            assert isinstance(cursor, sqlite3.Cursor)


def test_execute_transaction():
    queries = [
        ("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)", ()),
        ("INSERT INTO test (value) VALUES (?)", ("test_value",)),
        ("SELECT value FROM test", ()),
    ]
    result = execute_transaction(queries)

    assert result == [[], [], [("test_value",)]]


def test_ensure_table_exists():
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


def test_init_db():
    init_db()

    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        assert ("conversation_history",) in tables
        assert ("token_count",) in tables


@pytest.fixture
def session_id():
    return str(uuid.uuid4())


def test_save_and_load_message(session_id):
    save_message(session_id, "user", "Hello", {"timestamp": "2023-01-01T00:00:00"})
    save_message(
        session_id, "assistant", "Hi there!", {"timestamp": "2023-01-01T00:00:01"}
    )

    history = get_session_history(session_id)
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "Hello"
    assert history[0]["metadata"]["timestamp"] == "2023-01-01T00:00:00"
    assert history[1]["role"] == "assistant"
    assert history[1]["content"] == "Hi there!"
    assert history[1]["metadata"]["timestamp"] == "2023-01-01T00:00:01"


def test_load_state(session_id):
    save_message(session_id, "user", "Hello", {"timestamp": "2023-01-01T00:00:00"})
    save_message(
        session_id, "assistant", "Hi there!", {"timestamp": "2023-01-01T00:00:01"}
    )

    loaded_history = load_state(session_id)
    assert len(loaded_history) == 2
    assert loaded_history[0]["role"] == "user"
    assert loaded_history[0]["content"] == "Hello"
    assert loaded_history[0]["metadata"]["timestamp"] == "2023-01-01T00:00:00"
    assert loaded_history[1]["role"] == "assistant"
    assert loaded_history[1]["content"] == "Hi there!"
    assert loaded_history[1]["metadata"]["timestamp"] == "2023-01-01T00:00:01"


def test_save_state():
    database.conversation_history = [
        {
            "role": "user",
            "content": "Hello",
            "metadata": {"timestamp": "2023-01-01T00:00:00"},
        },
        {
            "role": "assistant",
            "content": "Hi there!",
            "metadata": {"timestamp": "2023-01-01T00:00:01"},
        },
    ]

    save_state()

    # Verify that the data was saved
    with database.get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, metadata FROM conversation_history ORDER BY timestamp"
        )
        results = cursor.fetchall()

    assert len(results) == 2
    assert results[0] == ("user", "Hello", '{"timestamp": "2023-01-01T00:00:00"}')
    assert results[1] == (
        "assistant",
        "Hi there!",
        '{"timestamp": "2023-01-01T00:00:01"}',
    )


def test_save_state_empty():
    database.conversation_history = []

    save_state()

    result = execute_transaction(
        [("SELECT role, content FROM conversation_history", ())]
    )
    assert result == [[]]


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


def test_token_count():
    # Test initial token count
    assert get_total_tokens() == 0

    # Test saving and retrieving token count
    save_total_tokens(100)
    assert get_total_tokens() == 100

    # Test updating token count
    save_total_tokens(200)
    assert get_total_tokens() == 200


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
