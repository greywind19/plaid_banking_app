"""
Tool registry for the agent.

Each tool is described in the OpenAI "function calling" format (so the model
knows what it can call) and mapped to a handler that runs the corresponding
service function. These are the SAME functions exposed over MCP in
mcp_server.py — the agent just reaches them in-process here. All read-only.
"""
from __future__ import annotations

from . import service

# --- JSON schema shared by tools that take a date range + account filter ---
_DATE_RANGE_PROPS = {
    "start": {"type": "string", "description": "Start date, inclusive, YYYY-MM-DD."},
    "end": {"type": "string", "description": "End date, inclusive, YYYY-MM-DD."},
    "account_ids": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Optional list of accountId values to filter to.",
    },
}


TOOL_SPECS = [
    {
        "type": "function",
        "function": {
            "name": "list_accounts",
            "description": "List all linked accounts with type, subtype, masked "
            "number, balances, and credit limit.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_balances",
            "description": "Get current/available balances and credit limits. "
            "Omit account_ids for all accounts.",
            "parameters": {
                "type": "object",
                "properties": {
                    "account_ids": _DATE_RANGE_PROPS["account_ids"],
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_transactions",
            "description": "Get normalized transactions, newest first. Each has "
            "date, name, amount, direction (outflow=spend, inflow=money in), "
            "category, and isTransfer. Use for listing or drill-down questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    **_DATE_RANGE_PROPS,
                    "count": {
                        "type": "integer",
                        "description": "Max number of transactions to return.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "spending_by_category",
            "description": "Total spending (outflows) grouped by category over a "
            "date range. Internal transfers and credit-card payments are excluded "
            "by default so nothing is double-counted. Use for 'where did my money "
            "go' / budget questions.",
            "parameters": {
                "type": "object",
                "properties": {
                    **_DATE_RANGE_PROPS,
                    "exclude_transfers": {
                        "type": "boolean",
                        "description": "Exclude transfers/card payments (default true).",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "net_worth",
            "description": "Compute net worth: assets (depository accounts) minus "
            "liabilities (credit accounts), with a per-account breakdown.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


# --- handlers: name -> callable(**args) -> JSON-serializable dict ----------
def _list_accounts(**_):
    return {"accounts": service.list_accounts()}


def _get_balances(account_ids=None, **_):
    return {"accounts": service.get_balances(account_ids)}


def _get_transactions(start=None, end=None, account_ids=None, count=None, **_):
    return {
        "transactions": service.get_transactions(
            start=start, end=end, account_ids=account_ids, count=count
        )
    }


def _spending_by_category(start=None, end=None, account_ids=None,
                          exclude_transfers=True, **_):
    return service.spending_by_category(
        start=start, end=end, account_ids=account_ids,
        exclude_transfers=exclude_transfers,
    )


def _net_worth(**_):
    return service.net_worth()


HANDLERS = {
    "list_accounts": _list_accounts,
    "get_balances": _get_balances,
    "get_transactions": _get_transactions,
    "spending_by_category": _spending_by_category,
    "net_worth": _net_worth,
}
