# Banking Copilot — Phase 1 (tool-testing build)

A personal-finance assistant grounded in real transaction data via **Plaid**.
This first build proves the Plaid connection end to end with a UI. No LLM yet —
the agent (Foundry hosted agent → MCP → Plaid) comes next.

```
User ──HTTP──▶ React UI ──/api──▶ REST server ─┐
                                                ├─▶ Plaid core service ──▶ Plaid Sandbox
Future: Foundry agent ──MCP(stdio)──▶ MCP server ┘
```

The **same core service** (`server/src/plaid/service.ts`) is exposed two ways:
- **REST API** (`http-server.ts`) — what the UI calls today.
- **MCP server** (`mcp-server.ts`) — what the agent will call later.

## Prerequisites

- Node 18+ (tested on Node 24)
- A free **Plaid** account → https://dashboard.plaid.com → copy your **client_id**
  and **sandbox secret**.

## Setup

```powershell
# 1. Server
cd banking-copilot\server
Copy-Item .env.example .env      # then edit .env with your Plaid sandbox creds
npm install

# 2. Web
cd ..\web
npm install
```

## Run (two terminals)

```powershell
# Terminal 1 — REST API on :8787
cd banking-copilot\server
npm run dev:api

# Terminal 2 — UI on :5173 (proxies /api to the server)
cd banking-copilot\web
npm run dev
```

Open http://localhost:5173 and click **Connect Plaid sandbox**. You'll see demo
accounts (checking, savings, credit card), balances, net worth, spending by
category, and recent transactions.

## Run the MCP server (for the future agent)

```powershell
cd banking-copilot\server
npm run start:mcp    # speaks MCP over stdio
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
