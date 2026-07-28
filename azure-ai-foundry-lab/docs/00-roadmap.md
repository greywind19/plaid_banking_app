# Learning Roadmap — Azure AI Foundry Hosted Agent (End to End)

This roadmap maps every box in the architecture diagram to concepts, tasks, and a
"definition of done" so you always know what "finished" looks like for each phase.

Estimated pace: ~1 phase per week at a few hours/week. Faster if full-time.

---

## Prerequisites (Day 0)

Install and verify:

- **Azure CLI** (`az version`) — sign in with `az login`
- **Terraform** (`terraform version`, >= 1.6)
- **Docker Desktop** (`docker version`)
- **Node.js** LTS (`node -v`) — for the React UI in Phase 3
- **Git** + a GitHub account (Phase 4)
- **VS Code** with the Azure, Terraform, and Bicep extensions

Concepts to skim before starting:
- Azure resource hierarchy: Tenant → Subscription → Resource Group → Resource
- Azure RBAC vs. access keys (why Managed Identity matters)
- What a container image / registry is

Definition of done: `az account show` returns your corporate subscription and
`terraform version` + `docker version` both succeed.

---

## Phase 1 — Core Hosted Agent

**Objective:** an Azure AI Foundry agent that answers a question using a deployed model.
No UI, no data stores, no networking yet.

Concepts:
- Azure AI Foundry **hub** vs **project**
- **Model deployment** (GPT-4o-mini) vs the underlying Azure OpenAI resource
- **Agent** = model + instructions + tools + orchestration
- Tokens, temperature, system prompt / instructions

Tasks:
1. Create an AI Foundry hub + project (portal first — see `phase-1-core-agent.md`).
2. Deploy `gpt-4o-mini`.
3. Create an agent, give it instructions, add one built-in tool (e.g. code interpreter).
4. Chat with it in the playground.
5. Reproduce the resources in `terraform/modules/foundry`.

Definition of done: the agent answers a multi-turn question in the playground, and
`terraform plan` shows the same resources you clicked together.

Docs: https://learn.microsoft.com/azure/ai-foundry/

---

## Phase 2 — Data Layer (Grounding + Memory)

**Objective:** ground the agent in your own documents (RAG) and persist conversations.

Concepts:
- **RAG** (retrieval-augmented generation): chunk → embed → store → retrieve → prompt
- **Vector search** in Azure AI Search; embeddings model deployment
- **Cosmos DB** for thread/message persistence
- **Blob Storage** for source documents & artifacts

Tasks:
1. Deploy Azure AI Search + a `text-embedding-3-small` deployment.
2. Upload a few PDFs to Blob Storage.
3. Build an index (integrated vectorization or a simple script).
4. Attach the index to the agent as a knowledge source.
5. Store conversation threads in Cosmos DB.

Definition of done: the agent cites content from your uploaded docs, and a second
conversation turn remembers the first (thread persisted in Cosmos).

Docs: https://learn.microsoft.com/azure/search/vector-search-overview

---

## Phase 3 — UI Layer

**Objective:** a web chat UI, containerized, running on Azure Container Instance (ACI).

Concepts:
- Calling the agent from a backend (never put keys in the browser)
- Dockerizing a web app; multi-stage builds
- ACI: lightweight single-container hosting

Tasks:
1. Build a minimal React chat UI + a thin backend (Node/Python) that calls the agent.
2. Run locally, then write a `Dockerfile`.
3. Push the image to a registry (local first, ACR in Phase 4).
4. Deploy to ACI; browse to it.

> Corporate caveat: if policy blocks ACI public IPs, use **Azure Container Apps** or
> **App Service** instead — same container, better networking/ingress options. The
> `terraform/modules/ui` module notes where to swap.

Definition of done: you can open a browser, chat with your agent through your own UI.

---

## Phase 4 — DevOps / CI-CD + IaC

**Objective:** every change flows GitHub → build → ACR → deploy, and all infra is Terraform.

Concepts:
- GitHub Actions workflows, secrets, OIDC federation to Azure (no stored credentials)
- **ACR**: private image registry, image scanning, geo-replication
- Terraform state, remote backend (Azure Storage), `plan`/`apply` in CI

Tasks:
1. Put UI source in GitHub.
2. Configure **OIDC** federated credentials (workload identity) so Actions can deploy
   without a stored service principal secret.
3. Workflow: build image → push to ACR → update the container app/instance.
4. Move Terraform state to a remote backend; run `terraform plan` on PRs.

Definition of done: a commit to `main` rebuilds the image and redeploys automatically;
`terraform apply` runs from CI against remote state.

Docs: https://learn.microsoft.com/azure/developer/github/connect-from-azure-openid-connect

---

## Phase 5 — Security & Private Networking

**Objective:** zero keys, private traffic, controlled egress. This is where corporate
policy stops fighting you and starts agreeing with you.

Concepts:
- **Managed Identity** + RBAC instead of API keys (system- vs user-assigned)
- **VNet**, subnets, **Private Endpoints**, Private DNS zones
- **NSG** / **UDR** (routing), **Azure Firewall** for egress control, **DLP** policies

Tasks:
1. Give the UI container a Managed Identity; grant it `Cognitive Services User` on the
   Foundry/OpenAI resource. Remove all keys from config.
2. Create a VNet; add Private Endpoints for OpenAI, AI Search, Cosmos, Storage, ACR.
3. Disable public network access on those services.
4. Route egress through Azure Firewall; allow only required FQDNs.

Definition of done: services have `public_network_access = Disabled`, the app still
works over private endpoints, and no keys exist in any config or pipeline.

Docs: https://learn.microsoft.com/azure/ai-services/cognitive-services-virtual-networks

---

## Phase 6 — Observability

**Objective:** you can see what the agent is doing and get alerted when it breaks.

Concepts:
- **Application Insights** distributed tracing (trace a request UI → agent → model)
- **Log Analytics Workspace** as the central sink
- **Azure Monitor** metrics, **alerts**, dashboards
- Token/cost tracking and latency SLOs

Tasks:
1. Wire App Insights into the UI backend and enable Foundry tracing.
2. Send all diagnostic settings to one Log Analytics workspace.
3. Build a dashboard: request volume, latency, token usage, errors.
4. Create alerts (error rate, latency, cost threshold).

Definition of done: a single trace shows the full hop chain, and a deliberately broken
deploy triggers an alert.

---

## Capstone

Tear the whole thing down (`terraform destroy`) and rebuild it from scratch with a
single `terraform apply` + one CI run. If it comes back green end to end, you've
learned the workflow.

## Cost control (important on any subscription)

- Use `gpt-4o-mini` and `text-embedding-3-small`, not the large models.
- Choose **Basic**/lowest SKUs for AI Search, Cosmos (serverless), Storage (LRS).
- `terraform destroy` at the end of every session; only pay for Phase work in progress.
- Set a **budget + cost alert** on the resource group on Day 0.
