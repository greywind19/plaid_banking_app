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
app/seed_data.py     custom-user blueprint → richer, realistic sandbox data
app/token_store.py   in-memory access_token + cached transactions
app/llm_client.py    LLM client factory (Foundry / OpenAI, chosen by env)
app/agent_tools.py   tool schemas + handlers (same tools as MCP) for the agent
app/agent.py         the LLM tool-calling loop (the copilot brain)
app/chat.py          terminal chat REPL to talk to the agent
```

## Seeded sandbox data

`connect_sandbox()` hands Plaid a [custom-user](https://plaid.com/docs/sandbox/user-custom/)
blueprint (`app/seed_data.py`) so the Sandbox builds three coherent accounts —
checking, savings, and a credit card — with a full month of realistic activity:
biweekly salary, rent + utilities, groceries/dining/subscriptions, a
checking→savings transfer, and a monthly card payment. The data lives **inside
Plaid**; we still fetch it through the same `/transactions/sync` path.

> Note: Plaid's Sandbox only surfaces custom transactions dated within the last
> ~30 days of Item creation (verified by testing; `days_requested` does not
> extend this for override data), so the seed models one rich ~29-day cycle
> rather than several months. Pass `use_seed=False` to `connect_sandbox()` for
> Plaid's default random data instead.

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

## Chat with the agent (the copilot brain)

The agent is an LLM that answers finance questions by calling the tools above
and explaining the results. Its model is chosen by `LLM_PROVIDER` in `.env`:
`foundry` (Azure AI Foundry / Azure OpenAI, default) or `openai`.

1. Deploy a model in [ai.azure.com](https://ai.azure.com) and copy its endpoint,
   key, deployment name, and API version into `.env` (see `.env.example`).
2. Run the terminal chat:

```powershell
cd banking-copilot\server-python
.\.venv\Scripts\python.exe -m app.chat
```

It links the seeded sandbox automatically, then you can ask things like
"what did I spend on this month?", "how much on dining?", or "what's my net
worth?". The model never sees Plaid credentials — only the JSON our read-only
tools return.

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
