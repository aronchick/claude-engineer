import os

import pytest

import database


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    os.environ["TESTING"] = "true"
    os.environ.setdefault("ANTHROPIC_API_KEY", "test_anthropic_key")
    os.environ.setdefault("TAVILY_API_KEY", "test_tavily_key")

    # Ensure the database is initialized
    database.init_db()

    yield

    # Clean up after all tests
    database.close_db_connection()


@pytest.fixture(autouse=True, scope="function")
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
