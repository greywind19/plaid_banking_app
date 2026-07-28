# Banking Copilot — Phase 1 (tool-testing build)

A personal-finance assistant grounded in real transaction data via **Plaid**.
This first build proves the Plaid connection end to end with a UI. No LLM yet —
the agent (Foundry hosted agent → MCP → Plaid) comes next.

```
User ──HTTP──▶ React UI ──/api──▶ REST server ─┐
                                                ├─▶ Plaid core service ──▶ Plaid Sandbox
Future: Foundry agent ──MCP(stdio)──▶ MCP server ┘
```

The **same core service** (`server-python/app/service.py`) is exposed two ways:
- **REST API** (`http_server.py`, FastAPI) — what the UI calls today.
- **MCP server** (`mcp_server.py`) — what the agent will call later.

Backend is **Python (FastAPI)**; frontend is **React + TypeScript**.

## Prerequisites

- **Python 3.11+** (tested on 3.12) and **Node 18+** (for the React UI)
- A free **Plaid** account → https://dashboard.plaid.com → copy your **client_id**
  and **sandbox secret**.

## Setup

```powershell
# 1. Backend (Python)
cd banking-copilot\server-python
Copy-Item .env.example .env      # then edit .env with your Plaid sandbox creds
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt

# 2. Web (React)
cd ..\web
npm install
```

## Run (two terminals)

```powershell
# Terminal 1 — REST API on :8787
cd banking-copilot\server-python
.\.venv\Scripts\python.exe -m app.http_server

# Terminal 2 — UI on :5173 (proxies /api to the server)
cd banking-copilot\web
npm run dev
```

Open http://localhost:5173 and click **Connect Plaid sandbox**. You'll see demo
accounts (checking, savings, credit card), balances, net worth, spending by
category, and recent transactions.

## Run the MCP server (for the future agent)

```powershell
cd banking-copilot\server-python
.\.venv\Scripts\python.exe -m app.mcp_server    # speaks MCP over stdio
```

Tools exposed (all **read-only**): `connect_sandbox`, `list_accounts`,
`get_balances`, `get_transactions`, `spending_by_category`, `net_worth`.

## Design notes

- **Sign normalization** — Plaid's amount sign is normalized to explicit
  `direction: outflow | inflow` so spend is always unambiguous across account types.
- **Transfer exclusion** — internal transfers and credit-card payments are flagged
  and excluded from spending totals so money movement isn't double-counted.
- **Secrets stay server-side** — the Plaid `access_token` and `secret` never reach
  the browser or (later) the model context.
- **Aggregation in the server** — category rollups and net worth are computed in the
  service, not by the model, so numbers are accurate and cheap.

## Not yet (later phases)

- LLM chat agent (Azure AI Foundry hosted agent) calling the MCP tools
- Persistence (Cosmos DB for threads, storage for tokens) — currently in-memory
- Multiple Items / real bank links (sandbox uses one test institution)
- Auth, private networking, observability
