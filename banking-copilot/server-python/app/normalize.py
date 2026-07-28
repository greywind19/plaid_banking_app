"""
Normalize messy Plaid objects into clean, camelCase dicts that the UI and the
future agent consume. Keeping keys in camelCase keeps the existing React client
(web/src/api.ts) unchanged.

Plaid amount sign convention (same across account types):
    amount > 0  => money leaving the account   (spend / charge)
    amount < 0  => money entering the account   (deposit / payment / refund)
"""
from typing import Any

_TRANSFER_PRIMARIES = {"TRANSFER_IN", "TRANSFER_OUT"}


def _pretty_category(primary: str | None) -> str:
    if not primary:
        return "Uncategorized"
    return " ".join(w.capitalize() for w in primary.split("_"))


def _get(obj: Any, key: str, default=None):
    """Plaid model objects support attribute access; guard for missing/None."""
    val = getattr(obj, key, default)
    return default if val is None else val


def normalize_transaction(t: Any) -> dict:
    pfc = getattr(t, "personal_finance_category", None)
    primary = getattr(pfc, "primary", None) if pfc else None
    detailed = getattr(pfc, "detailed", None) if pfc else None

    is_transfer = (
        primary in _TRANSFER_PRIMARIES
        or detailed == "LOAN_PAYMENTS_CREDIT_CARD_PAYMENT"
    )

    amount = float(_get(t, "amount", 0.0))

    return {
        "id": _get(t, "transaction_id"),
        "accountId": _get(t, "account_id"),
        "date": str(_get(t, "date")),
        "name": _get(t, "name"),
        "merchant": getattr(t, "merchant_name", None),
        "amount": abs(amount),
        "direction": "outflow" if amount > 0 else "inflow",
        "category": _pretty_category(primary),
        "detailedCategory": detailed,
        "isTransfer": bool(is_transfer),
        "currency": getattr(t, "iso_currency_code", None)
        or getattr(t, "unofficial_currency_code", None),
    }


def normalize_account(a: Any) -> dict:
    bal = a.balances
    return {
        "accountId": _get(a, "account_id"),
        "name": _get(a, "name"),
        "officialName": getattr(a, "official_name", None),
        "mask": getattr(a, "mask", None),  # last 4 only — never full number
        "type": str(_get(a, "type")),
        "subtype": str(a.subtype) if getattr(a, "subtype", None) else None,
        "currentBalance": getattr(bal, "current", None),
        "availableBalance": getattr(bal, "available", None),
        "creditLimit": getattr(bal, "limit", None),
        "currency": getattr(bal, "iso_currency_code", None)
        or getattr(bal, "unofficial_currency_code", None),
    }
