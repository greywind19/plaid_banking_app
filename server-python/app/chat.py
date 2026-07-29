"""
Terminal chat with the Banking Copilot agent.

Run:  py -m app.chat   (from banking-copilot/server-python, venv active)

On start it makes sure the Plaid sandbox is linked (seeded data), then loops:
you type a question, the agent calls tools and answers. Type 'exit' to quit.
"""
from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()  # read .env before importing modules that read the environment

from . import service            # noqa: E402
from .brain import run_brain, active_backend  # noqa: E402
from .llm_client import LLMConfigError, get_llm  # noqa: E402
from .token_store import token_store  # noqa: E402


def _ensure_linked() -> None:
    if not token_store.is_linked():
        print("Linking Plaid sandbox (seeded data)…")
        result = service.connect_sandbox()
        print(f"  linked {len(result['accounts'])} accounts, "
              f"{result['transactionCount']} transactions.\n")


def main() -> None:
    # Fail fast with a friendly message if the LLM isn't configured yet.
    try:
        _client, model = get_llm()
    except LLMConfigError as e:
        print(f"LLM not configured:\n  {e}")
        return
    print(f"Banking Copilot — model: {model} · backend: {active_backend()}")

    _ensure_linked()
    print("Ask about your accounts, spending, or net worth. Type 'exit' to quit.\n")

    history: list[dict] = []
    while True:
        try:
            user = input("you › ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user.lower() in ("exit", "quit", ":q"):
            break
        if not user:
            continue

        history.append({"role": "user", "content": user})
        try:
            answer, history = run_brain(history)
        except Exception as e:
            print(f"  [error] {e}\n")
            history.pop()  # drop the failed turn so the session can continue
            continue
        print(f"\ncopilot › {answer}\n")


if __name__ == "__main__":
    main()
