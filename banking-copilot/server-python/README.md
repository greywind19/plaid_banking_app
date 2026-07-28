# Banking Copilot — Python backend

FastAPI REST API (for the React UI) + Plaid Python SDK + Python MCP server.
Same endpoints and same clean layering as before — the React UI in `../web` is
unchanged and still talks to `http://localhost:8787`.

## Layers

```
app/http_server.py   REST wrapper (FastAPI)   ← the UI calls this today
app/mcp_server.py    MCP wrapper (stdio)      ← the agent calls this later
app/service.py       THE BRAINS: accounts, transactions, spending, net worth
app/normalize.py     Plaid objects → clean camelCase dicts (sign + transfers)
app/plaid_client.py  Plaid SDK client (reads .env)
app/token_store.py   in-memory access_token + cached transactions
```

## Setup

```powershell
cd banking-copilot\server-python
Copy-Item .env.example .env      # then edit with your Plaid sandbox creds
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run the REST API (for the UI)

```powershell
cd banking-copilot\server-python
.\.venv\Scripts\python.exe -m app.http_server
```

Serves on `http://localhost:8787`. Then start the UI (`../web`, `npm run dev`) and
open http://localhost:5173.

> Tip: for auto-reload during development you can instead run:
> `.\.venv\Scripts\python.exe -m uvicorn app.http_server:app --reload --port 8787`

## Run the MCP server (for the future agent)

```powershell
cd banking-copilot\server-python
.\.venv\Scripts\python.exe -m app.mcp_server
```

Tools (all **read-only**): `connect_sandbox`, `list_accounts`, `get_balances`,
`get_transactions`, `spending_by_category`, `net_worth`.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/health` | liveness + linked status |
| POST | `/api/connect` | bootstrap the sandbox Item + sync transactions |
| POST | `/api/sync` | re-sync transactions |
| GET  | `/api/accounts` | list accounts |
| GET  | `/api/balances` | balances (`?accountIds=a,b`) |
| GET  | `/api/transactions` | `?start=&end=&accountIds=&count=` |
| GET  | `/api/spending` | category rollup (`?includeTransfers=true` to keep transfers) |
| GET  | `/api/net-worth` | assets − liabilities |
