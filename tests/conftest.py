# tests/conftest.py
import os

import pytest

# Set up the test environment variables before any imports
os.environ["TESTING"] = "true"
os.environ.setdefault("ANTHROPIC_API_KEY", "test_anthropic_key")
os.environ.setdefault("TAVILY_API_KEY", "test_tavily_key")

import database  # Now import database after setting up the environment


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


@pytest.fixture(autouse=True, scope="function")
def reset_config_env(monkeypatch):
    """Reset environment variables for config after each test."""
    yield
    import config

    config.load_env()  # Reload environment variables after each test


@pytest.fixture(autouse=True)
def set_test_env():
    os.environ["TESTING"] = "true"
    os.environ.setdefault("ANTHROPIC_API_KEY", "test_anthropic_key")
    os.environ.setdefault("TAVILY_API_KEY", "test_tavily_key")
