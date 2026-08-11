# Non-secret variable values (safe to commit). Secrets go in
# secrets.auto.tfvars (gitignored) — copy secrets.auto.tfvars.example.

subscription_id = "61c69764-de07-4358-beec-91174c9ab5c3"
location        = "canadacentral"

# All the Foundry endpoint defaults live in variables.tf; override here only
# if they change.

# Stage 7.5 drift reconciliation: the live app was repointed to run the `local`
# backend through the APIM AI gateway (done via CLI in Step 2). Codified here so
# Terraform stops trying to revert it.
agent_backend         = "local"
azure_openai_endpoint = "https://apim-banking-bcaca1.azure-api.net"

# Stage 7.5 Easy Auth: client id of the out-of-band Entra app registration
# behind banking-ui login (non-secret). The matching secret lives in the
# gitignored secrets.auto.tfvars.
easyauth_client_id = "ec9453bd-6cd6-40d4-8407-1a521e82163e"
