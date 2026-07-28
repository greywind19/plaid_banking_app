"""FastAPI REST wrapper — the surface the React UI calls (port 8787)."""
import os

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from . import service
from .token_store import token_store

load_dotenv()

app = FastAPI(title="Banking Copilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _parse_account_ids(v: str | None) -> list[str] | None:
    if not v:
        return None
    ids = [s.strip() for s in v.split(",") if s.strip()]
    return ids or None


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request, exc: Exception):
    # Surface Plaid error bodies clearly instead of a bare 500.
    import json

    message = str(exc)
    code = None
    body = getattr(exc, "body", None)
    if body:
        try:
            parsed = json.loads(body)
            message = parsed.get("error_message", message)
            code = parsed.get("error_code")
        except Exception:
            pass
    print(f"[api] error: {message} ({code})")
    return JSONResponse(status_code=500, content={"error": message, "code": code})


@app.get("/api/health")
def health():
    return {"ok": True, "linked": token_store.is_linked()}


@app.post("/api/connect")
def connect():
    return service.connect_sandbox()


@app.post("/api/sync")
def sync():
    return {"transactionCount": service.sync_transactions()}


@app.get("/api/accounts")
def accounts():
    return {"accounts": service.list_accounts()}


@app.get("/api/balances")
def balances(accountIds: str | None = Query(default=None)):
    return {"accounts": service.get_balances(_parse_account_ids(accountIds))}


@app.get("/api/transactions")
def transactions(
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    accountIds: str | None = Query(default=None),
    count: int | None = Query(default=None),
):
    return {
        "transactions": service.get_transactions(
            start=start,
            end=end,
            account_ids=_parse_account_ids(accountIds),
            count=count,
        )
    }


@app.get("/api/spending")
def spending(
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    accountIds: str | None = Query(default=None),
    includeTransfers: bool = Query(default=False),
):
    return service.spending_by_category(
        start=start,
        end=end,
        account_ids=_parse_account_ids(accountIds),
        exclude_transfers=not includeTransfers,
    )


@app.get("/api/net-worth")
def net_worth():
    return service.net_worth()


def main():
    import uvicorn

    port = int(os.getenv("PORT", "8787"))
    print(f"[api] Banking Copilot REST API on http://localhost:{port}")
    print("[api] POST /api/connect to bootstrap the Plaid sandbox.")
    uvicorn.run(app, host="127.0.0.1", port=port)


if __name__ == "__main__":
    main()
