"""
Foundry Agent Service backend — the *managed* alternative to app/agent.py.

Where agent.py runs the whole tool-calling loop itself (Foundry = just a model),
this module registers a persistent Agent inside the Foundry project and lets the
service orchestrate Threads (conversation memory) and Runs (the loop).

The one part that stays on our side is *executing* the banking tools. Foundry
can't reach into our process to call Plaid, so custom function tools use the
"client-side" pattern: the run pauses in `requires_action`, hands us the tool
calls, we run them locally against our read-only service functions, and submit
the JSON results back. Foundry owns orchestration + memory; the data stays here.

Switch it on with AGENT_BACKEND=foundry (see app/brain.py). Needs:
    AZURE_AI_PROJECT_ENDPOINT   https://<resource>.services.ai.azure.com/api/projects/<project>
    AZURE_OPENAI_DEPLOYMENT     model deployment name (e.g. gpt-5.4-mini)
    AZURE_TENANT_ID             (optional) pin tenant for keyless az-login auth
"""
from __future__ import annotations

import json
import os
import time

from .agent_tools import HANDLERS, TOOL_SPECS

_AGENT_NAME = "banking-copilot"

# Cached across calls so we don't recreate the client / agent every turn.
_client = None
_agent_id: str | None = None
_thread_id: str | None = None


class FoundryConfigError(RuntimeError):
    """Raised when required Foundry project settings are missing."""


def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        raise FoundryConfigError(
            f"Missing required environment variable {name}. "
            f"Set your Foundry project endpoint + deployment in .env."
        )
    return val


def _credential():
    """Keyless credential, mirroring llm_client's tenant-pinning logic."""
    from azure.identity import AzureCliCredential, DefaultAzureCredential

    tenant = os.getenv("AZURE_TENANT_ID")
    if tenant:
        return AzureCliCredential(tenant_id=tenant)
    return DefaultAzureCredential()


def _get_client():
    global _client
    if _client is None:
        from azure.ai.agents import AgentsClient

        _client = AgentsClient(
            endpoint=_require("AZURE_AI_PROJECT_ENDPOINT"),
            credential=_credential(),
        )
    return _client


def _tool_definitions():
    """Rewrap our OpenAI-format TOOL_SPECS as Foundry FunctionToolDefinitions.

    Same schemas the local agent uses — only the wrapper class differs.
    """
    from azure.ai.agents.models import FunctionDefinition, FunctionToolDefinition

    defs = []
    for spec in TOOL_SPECS:
        fn = spec["function"]
        defs.append(
            FunctionToolDefinition(
                function=FunctionDefinition(
                    name=fn["name"],
                    description=fn.get("description", ""),
                    parameters=fn.get(
                        "parameters", {"type": "object", "properties": {}}
                    ),
                )
            )
        )
    return defs


def _get_or_create_agent(client) -> str:
    """Create the agent once, or reuse an existing one with the same name."""
    global _agent_id
    if _agent_id:
        return _agent_id

    # Reuse by name so repeated runs don't pile up duplicate agents.
    for existing in client.list_agents():
        if getattr(existing, "name", None) == _AGENT_NAME:
            _agent_id = existing.id
            return _agent_id

    # Reuse the local agent's system prompt for an apples-to-apples comparison.
    from .agent import _system_prompt

    agent = client.create_agent(
        model=_require("AZURE_OPENAI_DEPLOYMENT"),
        name=_AGENT_NAME,
        instructions=_system_prompt(),
        tools=_tool_definitions(),
    )
    _agent_id = agent.id
    return _agent_id


def _execute_tool_call(tool_call) -> dict:
    """Run one requested tool locally against our read-only service functions."""
    name = tool_call.function.name
    try:
        args = json.loads(tool_call.function.arguments or "{}")
    except json.JSONDecodeError:
        args = {}
    handler = HANDLERS.get(name)
    if handler is None:
        return {"error": f"unknown tool '{name}'"}
    try:
        return handler(**args)
    except Exception as e:  # surface tool errors back to the model
        return {"error": str(e)}


def _latest_answer(client) -> str:
    """Pull the newest assistant message text off the thread."""
    from azure.ai.agents.models import ListSortOrder

    messages = client.messages.list(
        thread_id=_thread_id, order=ListSortOrder.DESCENDING, limit=1
    )
    for msg in messages:
        # Prefer the convenience accessor; fall back to raw content parts.
        text_parts = getattr(msg, "text_messages", None)
        if text_parts:
            return text_parts[-1].text.value
        for part in getattr(msg, "content", []) or []:
            text = getattr(part, "text", None)
            if text is not None:
                return getattr(text, "value", "") or ""
    return ""


def run_foundry_agent(history: list[dict]) -> tuple[str, list[dict]]:
    """Run one assistant turn via Foundry Agent Service.

    Signature matches app/agent.run_agent so it's a drop-in backend. Foundry
    holds the real memory in the thread; we only push the newest user message
    and start a fresh thread when a new conversation begins.
    """
    from azure.ai.agents.models import (
        RequiredFunctionToolCall,
        SubmitToolOutputsAction,
        ToolOutput,
    )

    global _thread_id
    client = _get_client()
    agent_id = _get_or_create_agent(client)

    # The newest user message is the last user-role entry in history.
    user_msg = ""
    for m in reversed(history):
        if m.get("role") == "user" and m.get("content"):
            user_msg = m["content"]
            break

    # Fresh conversation (only the opening message) => new thread. Otherwise
    # reuse the existing thread so Foundry supplies the prior context for us.
    user_turns = len([m for m in history if m.get("role") == "user"])
    if _thread_id is None or user_turns <= 1:
        _thread_id = client.threads.create().id

    client.messages.create(thread_id=_thread_id, role="user", content=user_msg)
    run = client.runs.create(thread_id=_thread_id, agent_id=agent_id)

    # Poll the run, servicing tool calls when Foundry pauses for them.
    while run.status in ("queued", "in_progress", "requires_action"):
        if run.status == "requires_action" and isinstance(
            run.required_action, SubmitToolOutputsAction
        ):
            tool_calls = run.required_action.submit_tool_outputs.tool_calls
            outputs = []
            for tc in tool_calls:
                if isinstance(tc, RequiredFunctionToolCall):
                    result = _execute_tool_call(tc)
                    outputs.append(
                        ToolOutput(
                            tool_call_id=tc.id,
                            output=json.dumps(result, default=str),
                        )
                    )
            run = client.runs.submit_tool_outputs(
                thread_id=_thread_id, run_id=run.id, tool_outputs=outputs
            )
            continue

        time.sleep(0.6)
        run = client.runs.get(thread_id=_thread_id, run_id=run.id)

    if run.status == "failed":
        raise RuntimeError(
            f"Foundry run failed: {getattr(run, 'last_error', 'unknown')}"
        )

    answer = _latest_answer(client)
    return answer, history + [{"role": "assistant", "content": answer}]

