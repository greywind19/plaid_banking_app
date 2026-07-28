# Azure AI Foundry Hosted Agent — End-to-End Lab

A hands-on lab to build the full architecture: a hosted agent in Azure AI Foundry,
a containerized chat UI, a CI/CD pipeline, secure networking, and observability —
all provisioned with **Terraform**.

## Why this repo is structured in phases

You cannot learn (or debug) the whole diagram at once. Each phase produces something
that *works end to end*, then the next phase hardens or extends it. Get a green light
at each phase before moving on.

| Phase | Goal | Key services |
|-------|------|--------------|
| 1 | Core hosted agent talking to a model | AI Foundry, Azure OpenAI |
| 2 | Grounding + memory (RAG) | AI Search, Cosmos DB, Storage |
| 3 | Chat UI in a container | Container Instance, Docker |
| 4 | CI/CD + IaC | GitHub Actions, ACR, Terraform |
| 5 | Security & private networking | Entra ID / Managed Identity, VNet, Private Endpoints, Firewall |
| 6 | Observability | App Insights, Log Analytics, Azure Monitor, Alerts |

## Folder layout

```
azure-ai-foundry-lab/
├── README.md                 # you are here
├── docs/
│   ├── 00-roadmap.md         # full learning roadmap, concepts, links, checklists
│   └── phase-1-core-agent.md # hands-on: stand up the agent today
└── terraform/
    ├── README.md             # how to run the Terraform
    ├── versions.tf
    ├── providers.tf
    ├── variables.tf
    ├── main.tf               # wires modules together, phase by phase
    ├── outputs.tf
    ├── terraform.tfvars.example
    └── modules/
        ├── foundry/          # Phase 1: AI Foundry + Azure OpenAI
        ├── data/             # Phase 2: AI Search, Cosmos, Storage
        ├── ui/               # Phase 3: ACR + Container Instance
        ├── networking/       # Phase 5: VNet, subnets, private endpoints
        └── observability/    # Phase 6: Log Analytics, App Insights
```

## Corporate subscription notes

You're on a corporate subscription, so expect Azure Policy guardrails. Check these
**before** you start or `terraform apply` will fail in confusing ways:

- **Allowed regions** — you may be restricted to specific regions. Set `location` accordingly.
- **Required tags** — many tenants enforce tags (cost center, owner). See the `tags` var.
- **No public IPs / public network access** — you may be forced to use Private Endpoints
  from day one. If so, do Phase 5 networking *first*, then layer services onto it.
- **Deny Container Instance public IP** — if ACI public IP is blocked, plan to use
  Container Apps or App Service behind the VNet instead (noted in `docs/00-roadmap.md`).
- **Purview / DLP** — data exfiltration policies may block egress; that's what Phase 5 firewall teaches.

Run `az policy state list --filter "complianceState eq 'NonCompliant'"` after each apply to
see what tripped, and ask your platform team about a sandbox subscription or a
resource-group-scoped exemption for learning.

## Start here

1. Read `docs/00-roadmap.md` (concepts + full path).
2. Follow `docs/phase-1-core-agent.md` to get a working agent today.
3. Use `terraform/` to codify what you built by hand.
