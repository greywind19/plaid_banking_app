# Banking Copilot — Build Journal

A stage-by-stage record of how this app was built, the decisions made, and why.
Each stage is dated and self-contained so you can retrace the whole journey.

> **How to read this:** stages are in build order. ✅ = done, 🔜 = planned.
> Each stage has **What / Why / How / Files / How to verify**.

---

## Architecture at a glance (current)

```
Browser (React) ──/api──▶ FastAPI server ──▶ brain.py ─┬─▶ agent.py      (LOCAL loop)
                                                        └─▶ foundry_agent.py (FOUNDRY loop)
                              │                               │
                              ├─ agent_tools + service ──▶ Plaid Sandbox (cloud SaaS)
                              └─ (LLM / agent orchestration) ──▶ Azure AI Foundry (cloud)
```

- **Two interchangeable agent backends**, chosen at runtime by `AGENT_BACKEND`:
  - `local`  — our own tool-calling loop (`app/agent.py`), we own memory + loop.
  - `foundry`— Azure AI Foundry Agent Service (`app/foundry_agent.py`), Azure owns
    the loop + conversation memory (Threads/Runs); we only execute tools.
- **Foundry and Plaid are cloud services we call out to** — never containers.
- **Auth is keyless (Entra)** — `az login` in dev, Managed Identity in cloud, no
  code change (that's the whole reason we chose keyless on day one).

---

## Stage 1 — Plaid sandbox + core service ✅  (foundation)

**What:** A read-only finance service over Plaid's sandbox: accounts, balances,
transactions, spending-by-category, net worth.

**Why:** Ground the assistant in *real* transaction data before adding any AI, so
the agent has honest tools to call.

**How:** `service.py` wraps the Plaid client; `seed_data.py` seeds a richer custom
sandbox user so the numbers are interesting ($22,360.20 net worth, $3,951.35 spend).

**Files:** `app/service.py`, `app/plaid_client.py`, `app/normalize.py`,
`app/seed_data.py`, `app/token_store.py` (in-memory — see Stage 6 for the fix).

**Verify:** `POST /api/connect` then `GET /api/net-worth` → returns 22360.20.

---

## Stage 2 — Local agent brain (own tool loop) ✅

**What:** An LLM agent that answers finance questions by calling the Stage-1 tools.

**Why:** Learn the raw agent pattern: model decides which tool to call, we run it,
feed results back, repeat until it answers.

**How:** `agent.py` runs a `for` loop: `chat.completions.create(tools=TOOL_SPECS)`
→ if the model requests a tool, execute via `HANDLERS` and loop → else return text.
Provider is swappable via `llm_client.get_llm()` (Foundry model or OpenAI).

**Files:** `app/agent.py`, `app/agent_tools.py` (TOOL_SPECS + HANDLERS),
`app/llm_client.py`.

**Verify:** `python -m app.chat` → ask "What's my net worth?" → $22,360.20.

---

## Stage 3 — Keyless (Entra) auth ✅  (the cloud enabler)

**What:** Removed API keys; authenticate to Azure with the caller's identity.

**Why:** The tenant disables local/key auth by policy — and keyless is what makes
the later cloud move a *config* change, not a *code* change.

**How:** `llm_client` uses `AzureCliCredential`/`DefaultAzureCredential` +
`get_bearer_token_provider(..., "https://cognitiveservices.azure.com/.default")`.
`AZURE_TENANT_ID` pins the token to the MCAP tenant where the resource lives.

**Key learning — the credential ladder (unchanged code, three environments):**
`API key (n/a)` → `AzureCliCredential` (dev, `az login`) → `Managed Identity`
(cloud) — all via `DefaultAzureCredential` fallthrough.

**Files:** `app/llm_client.py`, `app/foundry_agent.py::_credential`.

**Verify:** with no `AZURE_OPENAI_API_KEY` set and `az login` done, chat still works.

---

## Stage 4 — Web chat UI ✅

**What:** A chat panel in the React dashboard talking to `POST /api/chat`.

**Why:** Make the agent usable in a browser, not just the terminal.

**How:** `/api/chat` accepts the full message history and returns the updated
history; React keeps the thread in state and re-sends it each turn.

**Files:** `app/http_server.py` (`/api/chat`, `ChatRequest`), `web/src/App.tsx`,
`web/src/api.ts`, `web/src/styles.css`.

**Verify:** http://localhost:5173 → ask a question in the chat panel.

---

## Stage 5 — Foundry Agent Service backend ✅  (managed agent)

**What:** A second backend where **Azure** runs the agent loop and holds memory.

**Why:** Graduate from "we own the loop" to a managed agent — the path to durable
memory, tracing, and evals without building them ourselves. This is the
"less dependency on the app" architecture: orchestration moves to the cloud.

**How:** `foundry_agent.py` uses `AgentsClient` (Threads/Runs). Foundry orchestrates;
when it needs a tool it pauses the run (`requires_action`), we execute the tool
locally and `submit_tool_outputs`. A persistent **Thread** gives conversation memory.
`brain.py` dispatches to `local` or `foundry` by the `AGENT_BACKEND` env var.

**What Azure now owns (vs the local loop):** the `for` loop, the model calls, and
the message/memory bookkeeping. **What stays local:** executing tools + Plaid data.

**RBAC learning:** Foundry splits data-plane permissions. Inference needs
*"Cognitive Services OpenAI User"*; the Agents API needs *"Foundry User"*
(`Microsoft.CognitiveServices/*`). Both granted on the resource.

**Files:** `app/foundry_agent.py`, `app/brain.py`; callers switched to `run_brain`.

**Verify:** `AGENT_BACKEND=foundry`, restart server, ask "net worth" ($22,360.20),
then "Of that, how much was dining?" ($521.05) → follow-up proves managed memory.

---

## Stage 6 — Containerize the stack (UI / server / Postgres) 🔜  *(in progress)*

**Goal:** Run the whole app as three containers via `docker compose` in Docker
Desktop, mirroring the eventual Azure Container Apps shape. Turn ephemeral state
durable (Postgres) so restarts/scaling don't lose the Plaid link.

**Why now:** Combines three lessons in one — persistence, containerization, and
multi-service networking — and produces a cloud-shaped artifact we can lift to ACA.

**Target architecture:**
```
docker compose (Docker Desktop)
  ├─ ui       (nginx serving React build, proxies /api → server)
  ├─ server   (uvicorn FastAPI; DATABASE_URL → postgres)
  └─ postgres (postgres:16-alpine, named volume for durable data)
        server ──HTTPS──▶ Azure Foundry (agent/model)   [OUTSIDE the box]
        server ──HTTPS──▶ Plaid Sandbox                  [OUTSIDE the box]
```

**Key design decisions (to be validated as we build):**
- **Postgres is wired, not decorative:** `token_store` (Plaid access_token, item_id,
  cursor, transaction cache) moves from in-memory → Postgres, keeping the same
  public methods so the rest of the app is untouched.
- **Foundry/Plaid stay outside the compose stack** — reached over HTTPS from the
  `server` container; they never become containers.
- **Auth across the container boundary:** there is no `az login` inside a container.
  Plan to use a **service principal** (client id/secret/tenant as env) — the closest
  local stand-in for the Managed Identity used later in Container Apps.

**Planned steps (each will be logged below as it lands):**
1. Postgres persistence for `token_store` (durable state).
2. `server/Dockerfile` + `.dockerignore`.
3. `ui/Dockerfile` (multi-stage: node build → nginx serve + `/api` proxy).
4. `docker-compose.yml` (3 services + volume + env wiring).
5. `docker compose up` → verify in Docker Desktop; confirm state survives
   `docker compose restart`.
6. Auth: service-principal env for the Foundry call from inside the container.

**Verify (target):** `docker compose up`, open the UI, chat works end-to-end via
the containerized server → Foundry; `docker compose restart` and the Plaid link +
Foundry thread both persist.

### Build log — Stage 6
_(entries appended as we complete each step)_

- **Decision (2026-07-29): DB = PostgreSQL, access via SQLAlchemy + psycopg3.**
  - Local container `postgres:16-alpine`; cloud twin = **Azure Database for
    PostgreSQL Flexible Server** (same wire protocol → same code, only
    `DATABASE_URL` + auth change). NOT Azure SQL Database (that's SQL Server).
  - Chose SQLAlchemy over raw psycopg for: connection **pooling** (Azure drops
    idle conns), a clean hook to inject **Entra tokens** as the DB password
    (keyless DB via `DefaultAzureCredential` — same pattern as Foundry:
    `az login` locally → Managed Identity in cloud, zero code change), and room
    to grow tables. `token_store` public methods stay identical so nothing else
    in the app changes.
- **✅ Step 1 done (2026-07-29) — Postgres persistence for `token_store`.**
  - New `app/db.py`: SQLAlchemy engine (`pool_pre_ping`) + `plaid_link` table
    (singleton row; access_token, item_id, cursor, transactions JSONB).
    `ensure_schema()` retries so the server can start before Postgres is ready.
    `_attach_entra_token()` is wired but dormant (only when `DB_USE_ENTRA=1`) —
    the Azure Managed-Identity DB-auth path, no code change to switch on.
  - Rewrote `app/token_store.py` into two backends behind the same interface:
    `InMemoryTokenStore` (unchanged behavior, used when DATABASE_URL is unset)
    and `PostgresTokenStore` (durable). Postgres exposes cursor/transactions as
    **properties** so `service.py`'s direct attribute writes persist with ZERO
    changes elsewhere. Backend picked by DATABASE_URL (config, not code).
  - Deps: added `sqlalchemy==2.0.36`, `psycopg[binary]==3.2.3`.
  - **Verified** against a throwaway `postgres:16-alpine`: linked + wrote
    cursor/transactions, then reloaded a fresh store object ("restart") — link,
    cursor, and 2 txns all survived. In-memory fallback still works with no
    DATABASE_URL. Test container removed.
- _next: step 2 — server Dockerfile + .dockerignore_

- **✅ Step 2 done (2026-07-29) — Server Dockerfile + .dockerignore.**
  - New `server-python/Dockerfile`: `python:3.12-slim`, deps installed as a
    cached layer (COPY requirements.txt before code), then `COPY app`. Runs
    `uvicorn app.http_server:app --host 0.0.0.0 --port 8787`. **Gotcha:** bind
    `0.0.0.0`, not `127.0.0.1` — inside a container 127.0.0.1 is unreachable
    from the host.
  - New `.dockerignore`: keeps `.venv`, `.env*` (secrets!), `__pycache__`, and
    scratch files out of the build context — smaller image, no leaked creds.
  - **Fixed a stale pin:** `requirements.txt` had `openai==1.109.1`, but
    `azure-ai-projects 2.4.0` now requires `openai>=2.8.0`. The build failed with
    `ResolutionImpossible`. The working venv actually runs `openai==2.50.0`, so
    bumped the pin to match. Lesson: the venv can drift from requirements.txt;
    the Docker build is a strict re-resolve that catches it.
  - **Verified in isolation:** built `banking-server:dev`, ran it on a Docker
    network with a `postgres:16-alpine` container. Server reached Postgres *by
    container name* (`pg-demo:5432`), auto-created `plaid_link` via
    `ensure_schema()`, and `GET /api/health` returned `{"ok":true,"linked":false}`.
    Containers + network removed after.
- _next: step 3 — UI Dockerfile (multi-stage node build → nginx serve + /api proxy)_

- **✅ Step 3 done (2026-07-29) — UI Dockerfile (multi-stage) + nginx.**
  - New `web/Dockerfile`: **two stages.** Stage 1 (`node:20-slim`) runs
    `npm ci` + `npm run build` → static bundle in `/app/dist`. Stage 2
    (`nginx:alpine`) copies ONLY `dist` + our `nginx.conf`. Final image has no
    Node and no source — just nginx + static files (small, clean).
  - New `web/nginx.conf`: two jobs — (1) **serve** the static React files with
    SPA fallback (`try_files ... /index.html`), and (2) **proxy** `/api/` →
    `http://server:8787` (the compose service name). The UI fetches relative
    `/api/...` (same as Vite dev proxy), so nginx replaces Vite in production.
  - **ACA note (documented in the file):** the `location /api` block is
    local-only. For ACA, delete those ~10 lines; the server gets its own ingress
    URL and the UI calls it directly. The Dockerfile + image are unchanged —
    nginx still serves the static UI in ACA and AKS. Only the proxy role is
    local.
  - New `web/.dockerignore`: excludes `node_modules`, `dist`, `.env*`.
  - **Verified the full trio** on a Docker network (postgres + server + ui):
    `GET :8080/` returned `<!doctype html>` (nginx serving), and
    `GET :8080/api/health` returned `{"ok":true,"linked":false}` (nginx proxied
    to server → Postgres). This is compose working by hand — Step 4 just
    formalizes it. Containers removed after.
- _next: step 4 — docker-compose.yml (ui + server + postgres, one `up`)_

- **✅ Step 4 done (2026-07-29) — docker-compose.yml.**
  - New `banking-copilot/docker-compose.yml`: 3 services — `postgres`
    (`postgres:16-alpine`), `server` (builds `./server-python`), `ui` (builds
    `./web`). One `docker compose up --build` replaces all the manual
    `docker run` + `docker network` commands from Steps 2–3.
  - **Named volume `pgdata`** → Postgres data survives `docker compose down`
    (lost only on `down -v`). This is the durability we test in Step 5.
  - **Healthcheck + depends_on:** `server` waits for `pg_isready` to pass before
    starting — no race on a cold `up`.
  - **Env wiring:** `server` uses `env_file: ./server-python/.env` (Plaid +
    Azure endpoints) and overrides `DATABASE_URL` to the `postgres` service name
    — which flips token_store into the durable Postgres backend automatically.
  - Ports: UI at `:8080`, server at `:8787` (exposed for direct curl testing;
    the UI reaches the server over the internal compose network via nginx).
  - `docker compose config` validates clean.
  - **Known limit (by design):** `/api/chat` needs Azure auth (`az login`),
    which doesn't exist inside a container → chat fails until **Step 6**
    (container auth / service principal). Everything else (health, connect,
    accounts, net worth, spending) works, because it's pure Plaid + Postgres.
- _next: step 5 — docker compose up + test in Docker Desktop (data path +
  persistence across restart)_

- **✅ Step 5 done (2026-07-29) — full stack tested in Docker Desktop.**
  - `docker compose up -d --build` built all 3 images and started them.
    Postgres reported **healthy** before the server started (depends_on +
    healthcheck gating worked — no cold-start race).
  - Data path verified end-to-end through the containers:
    - UI served at `:8080` (HTTP 200).
    - `/api/health` proxied through nginx → `{"ok":true,"linked":false}`.
    - `POST /api/connect` seeded Plaid sandbox: 3 accounts + 38 transactions.
    - `/api/net-worth` = **$22,360.20** (matches the known-good value from the
      pre-container runs — nothing regressed).
  - **Persistence proven twice:**
    1. `docker compose restart server` (server memory wiped) → still
       `linked:true`, net worth intact (read from Postgres, not memory).
    2. `docker compose down` (ALL containers removed, incl. Postgres) → `up`
       again → **still `linked:true`**. Data lived in the named `pgdata`
       volume, independent of any container. This is the durable-volume lesson.
  - **Chat deferred as planned:** `/api/chat` needs Azure auth (`az login`),
    absent in a container → Step 6 (container auth) lights it up.
  - Port note: had to stop an old host-side backend holding `:8787` before
    `up` (compose maps 8787→8787). Lesson: host port conflicts vs container
    port publishing.
- _next: step 6 — container auth for the Foundry/LLM call (service principal /
  DefaultAzureCredential), then open PR docker-stack → main_

- **✅ Step 6 done (2026-07-29) — container auth for Foundry via service principal.**
  - **Problem:** inside a container there's no `az login`, and the credential
    code short-circuited to `AzureCliCredential` whenever `AZURE_TENANT_ID` was
    set — which needs the `az` binary (absent in the slim image). So `/api/chat`
    failed in the container while everything else worked.
  - **Code fix:** added a service-principal branch to BOTH `llm_client.py` and
    `foundry_agent._credential()`. Credential ladder now:
    1. `AZURE_CLIENT_ID`+`SECRET`+`TENANT_ID` all set → `ClientSecretCredential`
       (containers / CI),
    2. else `AZURE_TENANT_ID` set → `AzureCliCredential` (local host az login,
       cross-tenant MCAP),
    3. else → `DefaultAzureCredential` (Managed Identity in Azure/ACA).
    Same code path scales local-container → cloud with zero further changes.
  - **Created the SP** `banking-copilot-local-sp` (portal, because tenant
    Conditional Access blocks `az ad sp create` from the CLI). Granted it the
    same two roles as the user — `Cognitive Services OpenAI User` +
    `Foundry User` — scoped to just `plaid-app-testing-resource`.
  - **Gotcha we hit (worth remembering):** the app was first read from the wrong
    directory (corp tenant `72f988bf`), so auth failed with `AADSTS700016 app
    not found in tenant bcea32b2`. The SP MUST live in the SAME tenant as the
    resource. Fix: use the app registered in the Fargo Post / MCAP directory
    (client id `067093ee-…`, not the corp `0c6cd791-…`). The **Object ID**
    (`61022d29-…`) matched, so the role assignments were already correct.
  - Creds go in `server-python/.env` (gitignored); documented as option (C) in
    `.env.example`. Compose passes them via `env_file`.
  - **Verified in-container:** rebuilt the server, `POST :8080/api/chat` →
    "Your net worth is **$22,360.20**" with a full asset/liability breakdown,
    through nginx → server (SP auth) → Foundry → tools → Postgres. Chat now
    works fully inside Docker.
- _next: open PR docker-stack → main (Stage 6 complete)_

---

## Stage 7 — deploy to Azure Container Apps with Terraform (2026-07-29)

**Goal:** take the exact same images from Stage 6 and run them in Azure
Container Apps (ACA), provisioned entirely by Terraform, with **keyless
Managed Identity auth to Foundry** — no secrets, no code changes.

### Infra as code (Terraform, `infra/`)
- `infra/modules/` — reusable modules, portable to AKS later:
  - `acr/` — Azure Container Registry (Basic, admin disabled).
  - `identity/` — user-assigned Managed Identity + 3 role assignments:
    `AcrPull` (pull images), `Cognitive Services OpenAI User` (inference),
    `Foundry User` (agents data plane) — the same two Foundry roles the local
    SP had, now bound to the MI.
  - `postgres/` — PostgreSQL Flexible Server (B1ms, v16) + `banking` DB +
    `AllowAzureServices` firewall rule. Outputs a sensitive `database_url`.
- `infra/aca/` — the compute layer: RG `rg-banking-copilot-aca`, ACA
  environment, and two container apps:
  - `banking-server` — **internal ingress only** (`external_enabled = false`),
    port 8787, MI attached. Secrets: database-url, plaid creds. The only auth
    env it gets is `AZURE_CLIENT_ID` = the MI's client id → the Stage 6
    credential ladder falls through to `DefaultAzureCredential`, which selects
    that user-assigned MI. **Zero secrets for Azure, zero code change.**
  - `banking-ui` — **public ingress** (`external_enabled = true`), port 80,
    nginx. `API_UPSTREAM = https://<server-internal-fqdn>`.

### nginx made portable
- Renamed `web/nginx.conf` → `web/nginx.conf.template` with `${API_UPSTREAM}`.
  `nginx:alpine` auto-runs envsubst on `/etc/nginx/templates/*.template` at
  boot. Locally that resolves to `http://server:8787`; in ACA to the internal
  HTTPS FQDN (template uses `$proxy_host` + `proxy_ssl_server_name on` so the
  Host header/SNI match ACA's internal ingress). Same image, both worlds.

### Reused existing infra (didn't create duplicates)
- Log Analytics: `data` source referencing the existing **FPlogs01**
  (`RG_Monitoring`) — Terraform reads it, never manages/deletes it.

### Deploy — the 4-phase runbook (chicken-and-egg: apps need images, images
need ACR)
1. `terraform apply "-target=azurerm_resource_group.this" "-target=module.acr"`
   → RG + ACR only. **PowerShell gotcha:** `-target` args MUST be quoted or
   PowerShell mangles them ("Too many command line arguments").
2. `az acr build --registry acrbankingbcaca1 --image banking-server:v1
   ./server-python` and `... banking-ui:v1 ./web` — cloud build, no local
   docker push. **Gotcha:** the Windows Azure CLI log streamer crashes with a
   `cp1252 'charmap' codec` UnicodeEncodeError — but **the build runs
   server-side regardless**; verify with `az acr repository show-tags` /
   `az acr task list-runs`, or use `--no-wait` and poll.
3. `terraform apply` (full) — Postgres is the slow one (~4 min), everything
   else seconds. 10 resources added.
4. Verify: `curl <ui_url>/api/health` → `{"ok":true,"linked":false}`, then
   `POST /api/chat {"messages":[{"role":"user","content":"…"}]}`.

### Result — live and verified
- Public URL:
  `https://banking-ui.proudsky-35a5a9f8.canadacentral.azurecontainerapps.io`
- `/api/health` → `{"ok":true,"linked":false}` (UI → nginx → internal server).
- `/api/chat` → real agent answer ("check balances, review transactions,
  summarize spending, calculate net worth") — proving the **full keyless
  chain in the cloud**: public UI → nginx → internal server → Managed Identity
  → `DefaultAzureCredential` → Foundry/LLM → tools → Postgres.
- The MI payoff confirmed: the first empty-body test reached Foundry and was
  rejected by *Foundry* (not a 401/403), i.e. the MI had already authenticated.

### Cost / teardown
- ~$17-20/mo if left running (Postgres B1ms always-on ~$12-15 is the driver;
  ACR Basic ~$5; ACA scales to zero when idle). `terraform destroy` stops
  billing — FPlogs01 is untouched (data source, not managed).

- _next: append merge note after PR; mirror to personal repo via
  `sync-to-personal.ps1` once Stage 7 lands on main._

---

## Backlog / future stages

- **Level 2 — Foundry tracing:** connect App Insights to the project → portal
  Tracing tab shows each Run's model + tool spans. (Started; parked.)
- **Level 3 — Evaluations:** score agent answer quality in the Foundry portal.
- **Ship to Azure Container Apps:** push images to ACR, deploy, enable Managed
  Identity (grant the same two roles, drop `AZURE_TENANT_ID` → zero code change),
  secrets → Key Vault, App Insights → tracing.
- **App hardening:** API auth, tighten CORS, pytest coverage on the tools,
  real Plaid Link flow for multi-user.
