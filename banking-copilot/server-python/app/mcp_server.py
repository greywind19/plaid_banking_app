"""
MCP server exposing the Plaid-backed banking tools over stdio. This is the
surface the future Foundry hosted agent will call. All tools are READ-ONLY.
"""
from mcp.server.fastmcp import FastMCP

from . import service

mcp = FastMCP("banking-copilot")


@mcp.tool()
def connect_sandbox() -> dict:
    """Bootstrap the Plaid sandbox: create a test bank Item, exchange the token,
    and sync transactions. Call this once before other tools."""
    return service.connect_sandbox()


@mcp.tool()
def list_accounts() -> dict:
    """List all linked accounts with type, subtype, masked number, and balances."""
    return {"accounts": service.list_accounts()}


@mcp.tool()
def get_balances(account_ids: list[str] | None = None) -> dict:
    """Get current/available balances (and credit limits) for accounts.
    Omit account_ids for all accounts."""
    return {"accounts": service.get_balances(account_ids)}


@mcp.tool()
def get_transactions(
    start: str | None = None,
    end: str | None = None,
    account_ids: list[str] | None = None,
    count: int | None = None,
) -> dict:
    """Get normalized transactions in a date range (YYYY-MM-DD).
    direction=outflow means spend."""
    return {
        "transactions": service.get_transactions(
            start=start, end=end, account_ids=account_ids, count=count
        )
    }


@mcp.tool()
def spending_by_category(
    start: str | None = None,
    end: str | None = None,
    account_ids: list[str] | None = None,
    exclude_transfers: bool = True,
) -> dict:
    """Aggregate spending (outflows) by category over a date range. Excludes
    internal transfers and credit-card payments by default so totals are not
    double-counted."""
    return service.spending_by_category(
        start=start,
        end=end,
        account_ids=account_ids,
        exclude_transfers=exclude_transfers,
    )


@mcp.tool()
def net_worth() -> dict:
    """Compute net worth: assets (depository accounts) minus liabilities
    (credit accounts)."""
    return service.net_worth()


if __name__ == "__main__":
    mcp.run()  # stdio transport by default
