# conftest.py
import pytest

import database


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
