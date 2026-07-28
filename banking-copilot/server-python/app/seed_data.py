"""
Seed data for the Plaid Sandbox custom user.

We do NOT fabricate data inside our app. Instead we hand Plaid a blueprint that
its Sandbox uses to build a bank; the app then fetches that data through the
same /transactions/sync path as always.

Plaid custom-user docs: https://plaid.com/docs/sandbox/user-custom/
- Pass override_username="user_custom" and override_password=<this JSON string>
  to /sandbox/public_token/create.
- Limits: max ~250 transactions and 10 accounts per user.

IMPORTANT constraint discovered by live testing:
  Plaid's Sandbox only surfaces custom override transactions dated within the
  last ~30 days of the Item's creation. Transactions dated older than that are
  silently dropped, and `options.transactions.days_requested` does NOT extend
  this for override data. So we model one realistic ~29-day cycle (a full month
  of income, bills, spending, a transfer, and a card payment) rather than
  several months. All dates are generated relative to today.

Sign convention for override transaction `amount` (verified live):
  positive = money out (spend / debit), negative = money in (income / credit).
  Centralized in _OUTFLOW / _INFLOW below in case Plaid ever changes it.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

# --- sign convention knobs (verified: positive = outflow) ------------------
_OUTFLOW = 1.0
_INFLOW = -1.0


def _spend(amount: float) -> float:
    return round(_OUTFLOW * abs(amount), 2)


def _income(amount: float) -> float:
    return round(_INFLOW * abs(amount), 2)


def _build_transactions(today: date):
    """One coherent ~29-day cycle across checking, savings, and credit card."""
    checking: list[dict] = []
    savings: list[dict] = []
    credit: list[dict] = []

    def ago(days: int) -> date:
        return today - timedelta(days=days)

    def txn(d: date, amount: float, description: str) -> dict:
        iso = d.isoformat()
        return {
            "date_transacted": iso,
            "date_posted": iso,
            "amount": amount,
            "description": description,
            "currency": "USD",
        }

    # --- Checking: income + fixed bills ---
    checking.append(txn(ago(28), _income(2600), "Acme Corp Payroll"))     # biweekly salary
    checking.append(txn(ago(14), _income(2600), "Acme Corp Payroll"))
    checking.append(txn(ago(27), _spend(1850), "Griffin Property Management Rent"))
    checking.append(txn(ago(26), _spend(118.40), "City Power & Water Utilities"))
    checking.append(txn(ago(25), _spend(79.99), "Xfinity Internet"))
    checking.append(txn(ago(24), _spend(72.50), "Verizon Wireless"))

    # --- Checking: weekly groceries + biweekly gas ---
    checking.append(txn(ago(25), _spend(96.20), "Whole Foods Market"))
    checking.append(txn(ago(18), _spend(74.85), "Trader Joes"))
    checking.append(txn(ago(11), _spend(112.40), "Safeway"))
    checking.append(txn(ago(4), _spend(63.75), "Whole Foods Market"))
    checking.append(txn(ago(20), _spend(46.30), "Shell Gas Station"))
    checking.append(txn(ago(6), _spend(51.10), "Shell Gas Station"))

    # --- Internal transfer checking -> savings (should be EXCLUDED from spend) ---
    checking.append(txn(ago(15), _spend(500), "Transfer to Savings"))
    savings.append(txn(ago(15), _income(500), "Transfer from Checking"))
    savings.append(txn(ago(2), _income(4.25), "Interest Payment"))

    # --- Monthly credit card payment (checking out, card balance down) — EXCLUDED ---
    checking.append(txn(ago(10), _spend(650), "Credit Card Payment"))
    credit.append(txn(ago(10), _income(650), "Payment Thank You"))

    # --- Credit card: subscriptions ---
    credit.append(txn(ago(27), _spend(15.49), "Netflix"))
    credit.append(txn(ago(20), _spend(10.99), "Spotify"))
    credit.append(txn(ago(12), _spend(14.99), "Amazon Prime"))
    credit.append(txn(ago(9), _spend(52.00), "Planet Fitness"))

    # --- Credit card: dining & coffee ---
    credit.append(txn(ago(26), _spend(6.75), "Starbucks"))
    credit.append(txn(ago(23), _spend(14.15), "Chipotle Mexican Grill"))
    credit.append(txn(ago(21), _spend(41.30), "Olive Garden"))
    credit.append(txn(ago(17), _spend(9.40), "Blue Bottle Coffee"))
    credit.append(txn(ago(13), _spend(28.65), "Sweetgreen"))
    credit.append(txn(ago(8), _spend(7.25), "Starbucks"))
    credit.append(txn(ago(5), _spend(19.80), "Chipotle Mexican Grill"))
    credit.append(txn(ago(2), _spend(46.55), "Olive Garden"))

    # --- Credit card: rideshare ---
    credit.append(txn(ago(24), _spend(13.20), "Uber"))
    credit.append(txn(ago(16), _spend(21.45), "Uber"))
    credit.append(txn(ago(7), _spend(17.10), "Uber"))

    # --- Credit card: shopping ---
    credit.append(txn(ago(22), _spend(64.99), "Amazon"))
    credit.append(txn(ago(14), _spend(129.50), "Target"))
    credit.append(txn(ago(6), _spend(89.00), "Best Buy"))
    credit.append(txn(ago(3), _spend(105.50), "Nike"))

    # --- Credit card: one travel splurge ---
    credit.append(txn(ago(21), _spend(465.00), "United Airlines"))
    credit.append(txn(ago(20), _spend(212.80), "Marriott Hotels"))

    return checking, savings, credit


def build_custom_user_config(today: date | None = None) -> dict:
    today = today or date.today()
    checking, savings, credit = _build_transactions(today)

    return {
        "seed": "banking-copilot-v1",
        "override_accounts": [
            {
                "type": "depository",
                "subtype": "checking",
                "starting_balance": 5200.75,
                "meta": {"name": "Everyday Checking", "official_name": "Everyday Checking Account", "mask": "1111"},
                "transactions": checking,
            },
            {
                "type": "depository",
                "subtype": "savings",
                "starting_balance": 18400.00,
                "meta": {"name": "Rainy Day Savings", "official_name": "High-Yield Savings", "mask": "2222"},
                "transactions": savings,
            },
            {
                "type": "credit",
                "subtype": "credit card",
                "starting_balance": 1240.55,
                "meta": {"name": "Everyday Rewards Card", "official_name": "Rewards Visa", "limit": 6000, "mask": "3333"},
                "transactions": credit,
            },
        ],
    }


def get_seed_password_json(today: date | None = None) -> str:
    return json.dumps(build_custom_user_config(today))


if __name__ == "__main__":
    cfg = build_custom_user_config()
    total = sum(len(a["transactions"]) for a in cfg["override_accounts"])
    print(f"accounts: {len(cfg['override_accounts'])}, transactions: {total}")
    print(f"config size: {len(get_seed_password_json())} bytes")
