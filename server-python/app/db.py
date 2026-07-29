"""
SQLAlchemy engine + schema for the durable token store (PostgreSQL).

Why SQLAlchemy + psycopg3 (not raw psycopg):
  * connection pooling (Azure managed Postgres drops idle connections)
  * a clean hook to inject Microsoft Entra tokens as the DB password, so the
    database is *keyless* too — same pattern as our Foundry auth
    (DefaultAzureCredential -> Managed Identity in cloud), no code change.

Local (docker compose):
    DATABASE_URL=postgresql+psycopg://banking:banking@postgres:5432/banking
Azure (later — Azure Database for PostgreSQL Flexible Server):
    DATABASE_URL=postgresql+psycopg://<mi-user>@<server>.postgres.database.azure.com:5432/banking
    DB_USE_ENTRA=1   # password supplied as a short-lived Entra token (Managed Identity)
"""
from __future__ import annotations

import os
import time

from sqlalchemy import Column, Integer, MetaData, Table, Text, create_engine
from sqlalchemy.dialects.postgresql import JSONB

metadata = MetaData()

# Single-row table (id is always 1). One linked Plaid Item for now; growing to
# multi-user later just means a real key instead of the fixed id.
link_table = Table(
    "plaid_link",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("access_token", Text, nullable=True),
    Column("item_id", Text, nullable=True),
    Column("cursor", Text, nullable=True),
    Column("transactions", JSONB, nullable=True),
)

_engine = None


def get_engine():
    """Create (once) and return the pooled SQLAlchemy engine."""
    global _engine
    if _engine is None:
        url = os.environ["DATABASE_URL"]
        _engine = create_engine(url, pool_pre_ping=True, future=True)
        if os.getenv("DB_USE_ENTRA") == "1":
            _attach_entra_token(_engine)
    return _engine


def ensure_schema(engine, retries: int = 10, delay: float = 1.5) -> None:
    """Create the table if missing. Retries so the server can start before
    Postgres is fully ready (compose brings them up together)."""
    last_err = None
    for _ in range(retries):
        try:
            metadata.create_all(engine)
            return
        except Exception as e:  # DB not accepting connections yet
            last_err = e
            time.sleep(delay)
    raise RuntimeError(f"Postgres not reachable after {retries} tries: {last_err}")


def _attach_entra_token(engine) -> None:
    """Inject a fresh Entra token as the DB password on every new connection.

    Mirrors the Foundry keyless pattern: DefaultAzureCredential picks up
    `az login` locally or Managed Identity in Azure. Only wired when
    DB_USE_ENTRA=1, so local username/password auth is unaffected.
    """
    from azure.identity import DefaultAzureCredential
    from sqlalchemy import event

    credential = DefaultAzureCredential()
    scope = "https://ossrdbms-aad.database.windows.net/.default"

    @event.listens_for(engine, "do_connect")
    def _provide_token(dialect, conn_rec, cargs, cparams):  # noqa: ANN001
        cparams["password"] = credential.get_token(scope).token
