"""
The agent: an LLM tool-calling loop.

Flow per user turn:
  1. Send the conversation + the tool catalog to the model.
  2. If the model asks to call tools, run them, append the results, and loop.
  3. When the model returns plain text, that's the answer.

The model never sees Plaid credentials — only the JSON that our read-only
service functions return.
"""
from __future__ import annotations

import json
from datetime import date

from .agent_tools import TOOL_SPECS, HANDLERS
from .llm_client import get_llm

_MAX_TOOL_ROUNDS = 6


def _system_prompt() -> str:
    return (
        "You are Banking Copilot, a concise personal-finance assistant. "
        f"Today's date is {date.today().isoformat()}. "
        "You answer questions about the user's accounts, transactions, spending, "
        "and net worth by calling the provided tools. Rules:\n"
        "- NEVER invent numbers. Always call a tool to get real figures before "
        "stating any amount.\n"
        "- A transaction with direction 'outflow' is money spent; 'inflow' is "
        "money received. Amounts are positive.\n"
        "- Transfers between the user's own accounts and credit-card payments are "
        "not spending; spending_by_category already excludes them.\n"
        "- Format money like $1,234.56. Be brief and specific; use short bullet "
        "lists for breakdowns.\n"
        "- If asked for advice, ground it in the actual data you retrieved."
    )


def run_agent(history: list[dict]) -> tuple[str, list[dict]]:
    """Run one assistant turn.

    history is a list of chat messages (without the system prompt). Returns the
    assistant's text answer plus the updated history (including tool traffic).
    """
    client, model = get_llm()

    messages = [{"role": "system", "content": _system_prompt()}, *history]

    for _ in range(_MAX_TOOL_ROUNDS):
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOL_SPECS,
            tool_choice="auto",
            # No temperature: reasoning models (gpt-5 / o-series) only accept the
            # default, and tool selection doesn't benefit from tuning it. Keeping
            # it unset makes this work across classic and reasoning deployments.
        )
        msg = resp.choices[0].message

        if not msg.tool_calls:
            answer = msg.content or ""
            messages.append({"role": "assistant", "content": answer})
            return answer, messages[1:]  # drop the system prompt

        # Record the assistant's tool-call request verbatim.
        messages.append(
            {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ],
            }
        )

        # Execute each requested tool and feed the result back.
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            handler = HANDLERS.get(name)
            if handler is None:
                result = {"error": f"unknown tool '{name}'"}
            else:
                try:
                    result = handler(**args)
                except Exception as e:  # surface tool errors to the model
                    result = {"error": str(e)}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, default=str),
                }
            )

    # Safety valve if the model kept calling tools without answering.
    fallback = "I wasn't able to finish that — please try rephrasing."
    messages.append({"role": "assistant", "content": fallback})
    return fallback, messages[1:]
