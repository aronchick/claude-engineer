from anthropic import Anthropic
from rich.console import Console
from rich.panel import Panel
from tavily import TavilyClient

import config as cfg
from chat import chat_with_claude
from database import save_state

console = Console()

# Add these constants at the top of the file
CONTINUATION_EXIT_PHRASE = cfg.CONTINUATION_EXIT_PHRASE
MAX_CONTINUATION_ITERATIONS = cfg.MAX_CONTINUATION_ITERATIONS

# Models to use
MAINMODEL = cfg.MAINMODEL
TOOLCHECKERMODEL = cfg.TOOLCHECKERMODEL

# Initialize the Anthropic client
client = Anthropic(api_key=cfg.ANTHROPIC_API_KEY)

# Initialize the Tavily client
tavily = TavilyClient(api_key=cfg.TAVILY_API_KEY)

# Set up the conversation memory
conversation_history = []

# automode flag
automode = False


def main():
    global automode, conversation_history
    console.print(
        Panel(
            "Welcome to the Claude-3-Sonnet Engineer Chat with Image Support!",
            title="Welcome",
            style="bold green",
        )
    )
    console.print("Type 'exit' to end the conversation.")
    console.print("Type 'image' to include an image in your message.")
    console.print(
        "Type 'automode [number]' to enter Autonomous mode with a specific number of iterations."
    )
    console.print(
        "While in automode, press Ctrl+C at any time to exit the automode to return to regular chat."
    )

    try:
        while True:
            user_input = console.input("[bold cyan]You:[/bold cyan] ")

            if user_input.lower() == "exit":
                console.print(
                    Panel(
                        "Thank you for chatting. Goodbye!",
                        title_align="left",
                        title="Goodbye",
                        style="bold green",
                    )
                )
                break

            if user_input.lower() == "image":
                image_path = console.input("Enter the path to your image: ")
                user_input = console.input("Enter your question about the image: ")
                response, _ = chat_with_claude(user_input, image_path)
            elif user_input.lower().startswith("automode"):
                try:
                    parts = user_input.split()
                    if len(parts) > 1 and parts[1].isdigit():
                        max_iterations = int(parts[1])
                    else:
                        max_iterations = MAX_CONTINUATION_ITERATIONS

                    automode = True
                    console.print(
                        Panel(
                            f"Entering automode with {max_iterations} iterations. Please provide the goal of the automode.",
                            title_align="left",
                            title="Automode",
                            style="bold yellow",
                        )
                    )
                    console.print(
                        Panel(
                            "Press Ctrl+C at any time to exit the automode loop.",
                            style="bold yellow",
                        )
                    )
                    user_input = console.input("[bold cyan]You:[/bold cyan] ")

                    iteration_count = 0
                    while automode and iteration_count < max_iterations:
                        response, exit_continuation = chat_with_claude(
                            user_input,
                            current_iteration=iteration_count + 1,
                            max_iterations=max_iterations,
                        )

                        if exit_continuation or CONTINUATION_EXIT_PHRASE in response:
                            console.print(
                                Panel(
                                    "Automode completed.",
                                    title_align="left",
                                    title="Automode",
                                    style="green",
                                )
                            )
                            automode = False
                        else:
                            console.print(
                                Panel(
                                    f"Continuation iteration {iteration_count + 1} completed. Press Ctrl+C to exit automode. ",
                                    title_align="left",
                                    title="Automode",
                                    style="yellow",
                                )
                            )
                            user_input = "Continue with the next step. Or STOP by saying 'AUTOMODE_COMPLETE' if you think you've achieved the results established in the original request."
                        iteration_count += 1

                        if iteration_count >= max_iterations:
                            console.print(
                                Panel(
                                    "Max iterations reached. Exiting automode.",
                                    title_align="left",
                                    title="Automode",
                                    style="bold red",
                                )
                            )
                            automode = False
                except KeyboardInterrupt:
                    console.print(
                        Panel(
                            "\nAutomode interrupted by user. Exiting automode.",
                            title_align="left",
                            title="Automode",
                            style="bold red",
                        )
                    )
                    automode = False
                    if (
                        conversation_history
                        and conversation_history[-1]["role"] == "user"
                    ):
                        conversation_history.append(
                            {
                                "role": "assistant",
                                "content": "Automode interrupted. How can I assist you further?",
                            }
                        )

                console.print(
                    Panel("Exited automode. Returning to regular chat.", style="green")
                )
            else:
                response, _ = chat_with_claude(user_input)
    except KeyboardInterrupt:
        console.print("\nKeyboard interrupt detected. Exiting the program.")
        automode = False
    finally:
        save_state()


if __name__ == "__main__":
    main()
