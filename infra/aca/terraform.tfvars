# Non-secret variable values (safe to commit). Secrets go in
# secrets.auto.tfvars (gitignored) — copy secrets.auto.tfvars.example.

subscription_id = "61c69764-de07-4358-beec-91174c9ab5c3"
location        = "canadacentral"

# All the Foundry endpoint defaults live in variables.tf; override here only
# if they change.
