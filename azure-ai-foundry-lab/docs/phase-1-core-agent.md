# Phase 1 — Stand Up the Core Hosted Agent (do this today)

Goal: an Azure AI Foundry agent chatting with a deployed model. ~60–90 minutes.
Do it in the **portal first** to understand the pieces, then codify with Terraform.

---

## Step 0 — Sign in and pick a region

```powershell
az login
az account set --subscription "<your-corporate-subscription-name-or-id>"
az account show --query "{name:name, id:id}" -o table
```

Check which regions your policy allows and which have Azure OpenAI capacity
(good defaults: `eastus2`, `swedencentral`). If a region is blocked, `az` will tell you.

```powershell
# See allowed locations if a policy restricts them
az policy assignment list --query "[].displayName" -o table
```

Set a budget alert on Day 0 so a runaway deployment can't surprise you:

```powershell
az consumption budget create --budget-name "ai-lab" --amount 50 --time-grain Monthly `
  --category Cost --start-date 2026-07-01 --end-date 2026-12-31 2>$null
# (If this cmd is unavailable in your tenant, set the budget in the Portal > Cost Management.)
```

---

## Step 1 — Create a resource group

```powershell
az group create --name rg-ai-foundry-lab --location swedencentral `
  --tags owner=$env:USERNAME purpose=learning env=lab
```

Adjust `--tags` to match any required tags your tenant enforces.

---

## Step 2 — Create the Foundry hub + project (Portal)

The portal is the clearest way to see the hub → project → deployment hierarchy the
first time.

1. Go to **https://ai.azure.com** → **+ New project**.
2. Create a **new hub** when prompted (this creates the underlying AI Services /
   OpenAI account, a Key Vault, and a Storage account behind the scenes).
3. Put it in `rg-ai-foundry-lab` and your chosen region.
4. Wait for deployment to finish, then open the project.

> What just happened: a **hub** is the shared, governed container (networking, connections,
> compute). A **project** is your workspace inside it. The hub owns an **Azure AI Services**
> resource that provides the OpenAI models.

---

## Step 3 — Deploy a model

1. In your project → **Models + endpoints** → **+ Deploy model** → **Deploy base model**.
2. Choose **gpt-4o-mini** (cheap, fast, plenty for a lab).
3. Name the deployment `gpt-4o-mini`. Keep default TPM/rate for now.
4. (For Phase 2 later) also deploy `text-embedding-3-small`.

---

## Step 4 — Create an agent

1. Project → **Agents** → **+ New agent**.
2. Give it instructions, e.g.:
   ```
   You are a lab assistant helping the user learn Azure AI Foundry.
   Answer concisely. If you use a tool, explain what you did.
   ```
3. Set the model to your `gpt-4o-mini` deployment.
4. Add one built-in tool — **Code Interpreter** is a good first one.
5. Open the **playground** and chat:
   - "What can you do?"
   - "Calculate the compound interest on $1000 at 5% for 3 years." (exercises the tool)
   - A follow-up question to confirm multi-turn memory.

Definition of done for the manual part: the agent answers, uses the tool, and remembers
context across turns.

---

## Step 5 — Codify it with Terraform

Now reproduce the core resources as code so you can destroy/rebuild at will.

```powershell
cd C:\Users\amansahota\.copilot\repos\my-work\azure-ai-foundry-lab\terraform
Copy-Item terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: subscription_id, location, tags, and set enable_foundry = true
terraform init
terraform plan
terraform apply
```

The `foundry` module provisions the AI Services account, an AI Foundry hub + project,
and the `gpt-4o-mini` deployment. Agents themselves are usually created via the SDK/portal
(the Terraform provider's agent support lags), so the module gives you everything the
agent *needs*, and you create the agent through the portal or the `azure-ai-agents` SDK.

> Verify the provider supports the Foundry resources in your pinned version — see
> `terraform/README.md`. If a resource type isn't available yet, the module comments
> show the `azapi` fallback.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `RequestDisallowedByPolicy` on create | Corporate Azure Policy | Read the error's `policyDefinitionName`; adjust region/tags/SKU or request an exemption |
| Model deploy fails: no quota | OpenAI quota not granted in region | Try another allowed region, or request quota in the Portal |
| `public network access is disabled` | Tenant forces private networking | Skip ahead to Phase 5 networking, then retry |
| Terraform: unknown resource type | Old azurerm provider | Bump the version in `versions.tf`; use the `azapi` fallback |

---

## Next

Once Phase 1 is green, move to `00-roadmap.md` → Phase 2 (data/grounding), and enable
the `data` module in `terraform/main.tf`.
