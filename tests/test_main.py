from unittest.mock import MagicMock, call, patch

import pytest
from rich.panel import Panel

import database
import main


@pytest.fixture(autouse=True)
def setup_and_teardown():
    # Setup
    database.DB_FILE = ":memory:"

    yield

    # Teardown
    if hasattr(database, "conversation_history"):
        database.conversation_history = []
    if hasattr(database, "total_tokens"):
        database.total_tokens = 0


@pytest.mark.parametrize(
    "user_input, expected_calls",
    [
        ("exit", 0),
        ("Hello", 1),
    ],
)
def test_main_exit_and_chat(user_input, expected_calls, monkeypatch):
    responses = iter([user_input, "exit"])
    monkeypatch.setattr("builtins.input", lambda: next(responses))

    with patch("main.chat_with_claude") as mock_chat:
        mock_chat.return_value = ("Claude response", False)
        main.main()
        assert mock_chat.call_count == expected_calls


def test_main_image_chat(monkeypatch):
    responses = iter(["image", "/path/to/image.jpg", "Describe this image", "exit"])
    monkeypatch.setattr("builtins.input", lambda: next(responses))
    monkeypatch.setattr(
        "os.path.isfile", lambda x: True
    )  # Mock os.path.isfile to always return True

    with patch("main.chat_with_claude") as mock_chat:
        mock_chat.return_value = ("Image description", False)
        main.main()
        mock_chat.assert_called_once_with(
            "Describe this image", image_path="/path/to/image.jpg"
        )


def test_main_automode(monkeypatch):
    responses = iter(["automode 3", "Automode goal", "exit"])
    monkeypatch.setattr("builtins.input", lambda: next(responses))

    with patch("main.chat_with_claude") as mock_chat:
        mock_chat.side_effect = [
            ("Step 1", False),
            ("Step 2", False),
            ("AUTOMODE_COMPLETE", True),
        ]
        main.main()
        assert mock_chat.call_count == 3


@patch("chat.get_client")
def test_chat_with_claude(mock_anthropic):
    mock_client = MagicMock()
    mock_anthropic.return_value = mock_client

    mock_response = MagicMock()
    mock_response.content = [MagicMock(type="text", text="Mock response")]
    mock_response.usage.input_tokens = 50
    mock_response.usage.output_tokens = 50

    mock_client.messages.create.return_value = mock_response

    response, exit_continuation = main.chat_with_claude("Test input")

    assert response == "Mock response"
    assert not exit_continuation
    assert database.get_total_tokens() == 100

    # Call chat_with_claude again to check if total_tokens accumulates
    response, exit_continuation = main.chat_with_claude("Test input 2")

    assert response == "Mock response"
    assert not exit_continuation
    assert database.get_total_tokens() == 200


def test_main_keyboard_interrupt():
    # Create a mock for Console.input
    with patch("main.console.input") as mock_console_input, patch(
        "main.chat_with_claude"
    ) as mock_chat, patch("main.save_state") as mock_save_state:
        # Set up the input sequence
        mock_console_input.side_effect = [
            "automode 3",  # Enter automode
            "Automode goal",  # Provide the automode goal
            "exit",  # Exit the program after returning to regular chat
        ]

        # Set up chat_with_claude mock to raise KeyboardInterrupt on the second call
        mock_chat.side_effect = [
            ("Response 1", False),
            KeyboardInterrupt(),
            ("Response 3", False),  # This call shouldn't happen
        ]

        # Run main()
        main.main()

        # Assertions
        assert not main.automode  # automode should be False after interruption

        # Check chat_with_claude calls
        assert mock_chat.call_count == 2  # chat_with_claude should be called twice
        mock_chat.assert_has_calls(
            [
                call("Automode goal", current_iteration=1, max_iterations=3),
                call(
                    "Continue with the next step. Or STOP by saying 'AUTOMODE_COMPLETE' if you think you've achieved the results established in the original request.",
                    current_iteration=2,
                    max_iterations=3,
                ),
            ]
        )

        assert (
            mock_console_input.call_count == 3
        )  # Console.input should be called 3 times

        resultPanel = Panel(
            "\nAutomode interrupted by user. Exiting automode.",
            title_align="left",
            title="Automode",
            style="bold red",
        )

        # Check that save_state was called
        mock_save_state.assert_called_once()
