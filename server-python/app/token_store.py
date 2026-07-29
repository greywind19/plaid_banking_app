"""
Token + sync-state store for the linked Plaid Item.

Holds the Plaid access_token, item_id, sync cursor, and the cached transactions.
The access_token / secret NEVER leave the server.

Two interchangeable backends, chosen by DATABASE_URL (same config-not-code
pattern as AGENT_BACKEND and keyless auth):

  * DATABASE_URL unset -> InMemoryTokenStore  (ephemeral; fine for quick dev,
                          but state is lost on restart)
  * DATABASE_URL set   -> PostgresTokenStore  (durable; survives restarts and is
                          shared across replicas, so the server stays stateless
                          and scales horizontally)

Both expose the identical surface the rest of the app already uses:
    attributes: access_token, item_id, cursor, transactions
    methods:    is_linked(), set_item(access_token, item_id), require_token(), reset()

PostgresTokenStore exposes cursor/transactions as *properties* so that existing
code like `token_store.transactions = collected` transparently persists to the
DB with no changes elsewhere (see app/service.py).
"""
from __future__ import annotations

import os

_NOT_LINKED_MSG = (
    "No linked account. Call /api/connect first to bootstrap the "
    "Plaid sandbox Item."
)


class InMemoryTokenStore:
    """Ephemeral store — the original behavior. State dies with the process."""

    def __init__(self) -> None:
        self.access_token: str | None = None
        self.item_id: str | None = None
        self.cursor: str | None = None
        self.transactions: list[dict] = []

    def is_linked(self) -> bool:
        return self.access_token is not None

    def set_item(self, access_token: str, item_id: str) -> None:
        self.access_token = access_token
        self.item_id = item_id
        self.cursor = None
        self.transactions = []

    def require_token(self) -> str:
        if not self.access_token:
            raise RuntimeError(_NOT_LINKED_MSG)
        return self.access_token

    def reset(self) -> None:
        self.__init__()


class PostgresTokenStore:
    """Durable store backed by a single `plaid_link` row in PostgreSQL.

    Reads hit the DB so every replica sees the same state (the point of moving
    off in-memory). The row is tiny and indexed by primary key, so this is cheap.
    """

    def __init__(self) -> None:
        from .db import ensure_schema, get_engine, link_table

        self._engine = get_engine()
        ensure_schema(self._engine)
        self._t = link_table

    # --- low-level row helpers -------------------------------------------------
    def _row(self) -> dict | None:
        from sqlalchemy import select

        with self._engine.connect() as conn:
            r = conn.execute(
                select(self._t).where(self._t.c.id == 1)
            ).mappings().first()
            return dict(r) if r else None

    def _upsert(self, **fields) -> None:
        """Insert-or-update the singleton row, touching only the given fields."""
        from sqlalchemy.dialects.postgresql import insert

        with self._engine.begin() as conn:
            stmt = insert(self._t).values(id=1, **fields)
            stmt = stmt.on_conflict_do_update(
                index_elements=[self._t.c.id], set_=fields
            )
            conn.execute(stmt)

    # --- attributes exposed as DB-backed properties ---------------------------
    @property
    def access_token(self) -> str | None:
        r = self._row()
        return r["access_token"] if r else None

    @access_token.setter
    def access_token(self, value: str | None) -> None:
        self._upsert(access_token=value)

    @property
    def item_id(self) -> str | None:
        r = self._row()
        return r["item_id"] if r else None

    @item_id.setter
    def item_id(self, value: str | None) -> None:
        self._upsert(item_id=value)

    @property
    def cursor(self) -> str | None:
        r = self._row()
        return r["cursor"] if r else None

    @cursor.setter
    def cursor(self, value: str | None) -> None:
        self._upsert(cursor=value)

    @property
    def transactions(self) -> list[dict]:
        r = self._row()
        if r and r["transactions"]:
            return r["transactions"]
        return []

    @transactions.setter
    def transactions(self, value: list[dict]) -> None:
        self._upsert(transactions=value)

    # --- same public methods as the in-memory store ---------------------------
    def is_linked(self) -> bool:
        r = self._row()
        return bool(r and r["access_token"])

    def set_item(self, access_token: str, item_id: str) -> None:
        # Single write so a new link atomically resets cursor + cache.
        self._upsert(
            access_token=access_token,
            item_id=item_id,
            cursor=None,
            transactions=[],
        )

    def require_token(self) -> str:
        token = self.access_token
        if not token:
            raise RuntimeError(_NOT_LINKED_MSG)
        return token

    def reset(self) -> None:
        from sqlalchemy import delete

        with self._engine.begin() as conn:
            conn.execute(delete(self._t).where(self._t.c.id == 1))


def _make_store():
    """Pick the backend from the environment (config, not code)."""
    if os.getenv("DATABASE_URL"):
        return PostgresTokenStore()  # fail loud if a configured DB is unreachable
    return InMemoryTokenStore()


token_store = _make_store()
