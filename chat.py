from anthropic import Anthropic
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from config import ANTHROPIC_API_KEY, MAINMODEL, MAX_TOKENS
from database import (
    conversation_history,
    get_total_tokens,
    save_state,
    save_total_tokens,
)
from prompts import update_system_prompt
from tools import execute_tool, tools

console = Console()


def get_client():
    return Anthropic(api_key=ANTHROPIC_API_KEY)


def chat_with_claude(
    user_input, image_path=None, current_iteration=None, max_iterations=None
):
    global conversation_history
    client = get_client()

    total_tokens = get_total_tokens()
    if total_tokens >= MAX_TOKENS:
        console.print(
            Panel(
                "Token limit reached. Please start a new session.",
                title="Token Limit",
                style="bold red",
            )
        )
        return "Token limit reached. Please start a new session.", False

    current_conversation = []

    if image_path:
        # Handle image processing here (not implemented in this example)
        pass
    else:
        current_conversation.append({"role": "user", "content": user_input})

    messages = conversation_history + current_conversation

    try:
        response = client.messages.create(
            model=MAINMODEL,
            max_tokens=4000,
            system=update_system_prompt(current_iteration, max_iterations),
            messages=messages,
            tools=tools,
            tool_choice={"type": "auto"},
        )
    except Exception as e:
        console.print(
            Panel(f"API Error: {str(e)}", title="API Error", style="bold red")
        )
        return (
            "I'm sorry, there was an error communicating with the AI. Please try again.",
            False,
        )

    assistant_response = ""
    exit_continuation = False
    tool_uses = []

    for content_block in response.content:
        if content_block.type == "text":
            assistant_response += content_block.text
        elif content_block.type == "tool_use":
            tool_uses.append(content_block)

    console.print(
        Panel(
            Markdown(assistant_response),
            title="Claude's Response",
            title_align="left",
            expand=False,
        )
    )

    for tool_use in tool_uses:
        tool_name = tool_use.name
        tool_input = tool_use.input
        tool_use_id = tool_use.id

        console.print(Panel(f"Tool Used: {tool_name}", style="green"))
        console.print(Panel(f"Tool Input: {tool_input}", style="green"))

        result = execute_tool(tool_name, tool_input)
        console.print(
            Panel(result, title_align="left", title="Tool Result", style="green")
        )

        current_conversation.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_name,
                        "input": tool_input,
                    }
                ],
            }
        )
        current_conversation.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": result,
                    }
                ],
            }
        )

    conversation_history = messages + [
        {"role": "assistant", "content": assistant_response}
    ]

    new_tokens = response.usage.input_tokens + response.usage.output_tokens
    save_total_tokens(total_tokens + new_tokens)

    save_state()

    return assistant_response, exit_continuation
