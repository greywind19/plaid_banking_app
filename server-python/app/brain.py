"""
Backend dispatcher: pick the agent implementation at runtime.

AGENT_BACKEND=local   (default) — app/agent.py runs the tool-loop itself.
AGENT_BACKEND=foundry           — app/foundry_agent.py uses Foundry Agent
                                  Service (managed Threads + Runs).

Both expose the same run(history) -> (answer, history) contract, so callers
(chat.py, http_server.py) don't care which one is active.
"""
from __future__ import annotations

import os


def run_brain(history: list[dict]) -> tuple[str, list[dict]]:
    backend = os.getenv("AGENT_BACKEND", "local").strip().lower()
    if backend == "foundry":
        from .foundry_agent import run_foundry_agent

        return run_foundry_agent(history)

    from .agent import run_agent

    return run_agent(history)


def active_backend() -> str:
    return os.getenv("AGENT_BACKEND", "local").strip().lower()
