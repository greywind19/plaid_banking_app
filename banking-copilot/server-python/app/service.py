"""
Core banking service. Every capability the UI (and later the agent) needs is a
plain function here. The REST (http_server) and MCP (mcp_server) layers are thin
wrappers around these functions.
"""
import json
import time

import plaid
from plaid.model.sandbox_public_token_create_request import (
    SandboxPublicTokenCreateRequest,
)
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.transactions_sync_request import TransactionsSyncRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.products import Products

from .plaid_client import client, SANDBOX_INSTITUTION_ID
from .normalize import normalize_account, normalize_transaction
from .token_store import token_store


def _round2(n: float) -> float:
    return round(n, 2)


def connect_sandbox() -> dict:
    """Bootstrap a Plaid sandbox Item and sync its transactions."""
    # 1. Create a sandbox public_token for the test institution.
    pt_req = SandboxPublicTokenCreateRequest(
        institution_id=SANDBOX_INSTITUTION_ID,
        initial_products=[Products("transactions")],
    )
    pt_resp = client.sandbox_public_token_create(pt_req)

    # 2. Exchange it for a durable access_token.
    ex_req = ItemPublicTokenExchangeRequest(public_token=pt_resp["public_token"])
    ex_resp = client.item_public_token_exchange(ex_req)

    access_token = ex_resp["access_token"]
    item_id = ex_resp["item_id"]
    token_store.set_item(access_token, item_id)

    # 3. Sync transactions into the in-memory cache.
    transaction_count = sync_transactions()

    return {
        "itemId": item_id,
        "accounts": list_accounts(),
        "transactionCount": transaction_count,
    }


def sync_transactions(max_polls: int = 12) -> int:
    """
    Pull all transactions via /transactions/sync.

    On a freshly created sandbox Item, Plaid is still generating history, so the
    first sync often returns an empty page with has_more=false. We therefore
    poll: fully drain each round, and if nothing has arrived yet, wait and call
    again with the retained cursor until data shows up (or PRODUCT_NOT_READY
    clears).
    """
    access_token = token_store.require_token()
    collected: list[dict] = []
    cursor: str | None = None

    for _ in range(max_polls):
        has_more = True
        while has_more:
            try:
                kwargs = {"access_token": access_token, "count": 500}
                if cursor is not None:
                    kwargs["cursor"] = cursor
                resp = client.transactions_sync(TransactionsSyncRequest(**kwargs))
                for t in resp["added"]:
                    collected.append(normalize_transaction(t))
                cursor = resp["next_cursor"]
                has_more = resp["has_more"]
            except plaid.ApiException as e:
                body = {}
                try:
                    body = json.loads(e.body)
                except Exception:
                    pass
                if body.get("error_code") == "PRODUCT_NOT_READY":
                    break  # not ready yet — fall through to the wait below
                raise

        if collected:
            break  # got data, done
        time.sleep(2)  # still preparing — wait and poll again

    token_store.cursor = cursor
    token_store.transactions = collected
    return len(collected)


def list_accounts() -> list[dict]:
    access_token = token_store.require_token()
    resp = client.accounts_get(AccountsGetRequest(access_token=access_token))
    return [normalize_account(a) for a in resp["accounts"]]


def get_balances(account_ids: list[str] | None = None) -> list[dict]:
    access_token = token_store.require_token()
    resp = client.accounts_balance_get(
        AccountsBalanceGetRequest(access_token=access_token)
    )
    accounts = [normalize_account(a) for a in resp["accounts"]]
    if account_ids:
        wanted = set(account_ids)
        accounts = [a for a in accounts if a["accountId"] in wanted]
    return accounts


def _in_range(date_str: str, start: str | None, end: str | None) -> bool:
    if start and date_str < start:
        return False
    if end and date_str > end:
        return False
    return True


def get_transactions(
    start: str | None = None,
    end: str | None = None,
    account_ids: list[str] | None = None,
    count: int | None = None,
) -> list[dict]:
    account_set = set(account_ids) if account_ids else None
    result = [
        t
        for t in token_store.transactions
        if _in_range(t["date"], start, end)
        and (account_set is None or t["accountId"] in account_set)
    ]
    result.sort(key=lambda t: t["date"], reverse=True)  # newest first
    if count and count > 0:
        result = result[:count]
    return result


def spending_by_category(
    start: str | None = None,
    end: str | None = None,
    account_ids: list[str] | None = None,
    exclude_transfers: bool = True,
) -> dict:
    """Sum outflows by category, excluding internal transfers/card payments."""
    txns = [
        t
        for t in get_transactions(start, end, account_ids)
        if t["direction"] == "outflow"
        and (not exclude_transfers or not t["isTransfer"])
    ]

    by_cat: dict[str, dict] = {}
    total_spend = 0.0
    for t in txns:
        total_spend += t["amount"]
        entry = by_cat.setdefault(
            t["category"], {"category": t["category"], "total": 0.0, "count": 0}
        )
        entry["total"] = _round2(entry["total"] + t["amount"])
        entry["count"] += 1

    categories = sorted(by_cat.values(), key=lambda c: c["total"], reverse=True)
    return {"totalSpend": _round2(total_spend), "categories": categories}


def net_worth() -> dict:
    """assets (depository) minus liabilities (credit) across all accounts."""
    accounts = get_balances()
    assets = 0.0
    liabilities = 0.0
    breakdown = []
    for a in accounts:
        bal = a["currentBalance"] or 0.0
        is_credit = a["type"] == "credit"
        if is_credit:
            liabilities += bal
        else:
            assets += bal
        breakdown.append(
            {
                "accountId": a["accountId"],
                "name": a["name"],
                "type": a["type"],
                "balance": bal,
                "sign": "liability" if is_credit else "asset",
            }
        )
    return {
        "assets": _round2(assets),
        "liabilities": _round2(liabilities),
        "netWorth": _round2(assets - liabilities),
        "breakdown": breakdown,
    }
