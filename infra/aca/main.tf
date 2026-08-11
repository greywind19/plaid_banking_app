# ============================================================================
# Stage 7 — Banking Copilot on Azure Container Apps
# One `terraform apply` builds: RG → ACR + Postgres + Managed Identity →
# Container Apps Environment → server (internal) + ui (public nginx front door).
# ============================================================================

resource "azurerm_resource_group" "this" {
  name     = var.resource_group_name
  location = var.location
  tags     = var.tags
}

# ---- Logs backing the Container Apps Environment ---------------------------
# Reuse the existing shared workspace (FPlogs01 in RG_Monitoring) rather than
# creating a new one. Data source = read-only reference; Terraform never
# modifies or deletes it.
data "azurerm_log_analytics_workspace" "shared" {
  name                = var.log_analytics_workspace_name
  resource_group_name = var.log_analytics_resource_group_name
}

# ---- Shared building blocks (reused by an AKS root later) ------------------
module "acr" {
  source              = "../modules/acr"
  name                = "acrbanking${var.name_suffix}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  tags                = var.tags
}

module "identity" {
  source              = "../modules/identity"
  name                = "id-banking-copilot"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  subscription_id     = var.subscription_id
  acr_id              = module.acr.id
  foundry_resource_id = var.foundry_resource_id
  tags                = var.tags
}

module "postgres" {
  source                 = "../modules/postgres"
  name                   = "psql-banking-${var.name_suffix}"
  resource_group_name    = azurerm_resource_group.this.name
  location               = azurerm_resource_group.this.location
  administrator_password = var.postgres_admin_password
  admin_ip_address       = var.admin_ip_address
  tags                   = var.tags
}

# ---- Stage 7.5: APIM AI Gateway (Consumption) -----------------------------
# Provisions the APIM instance + system MI only. The AOAI backend, imported
# API, and governance policies are layered on in later Stage 7.5 steps.
module "apim" {
  source              = "../modules/apim"
  name                = "apim-banking-${var.name_suffix}"
  resource_group_name = azurerm_resource_group.this.name
  location            = azurerm_resource_group.this.location
  publisher_name      = var.apim_publisher_name
  publisher_email     = var.apim_publisher_email
  tags                = var.tags
}

# ---- Container Apps Environment (the managed, hidden-K8s host) --------------
resource "azurerm_container_app_environment" "this" {
  name                       = "cae-banking-copilot"
  resource_group_name        = azurerm_resource_group.this.name
  location                   = azurerm_resource_group.this.location
  log_analytics_workspace_id = data.azurerm_log_analytics_workspace.shared.id
  tags                       = var.tags
}

# ============================================================================
# server — FastAPI backend. INTERNAL ingress only (never public). Reaches
# Foundry via the managed identity; reaches Postgres over its private hostname.
# ============================================================================
resource "azurerm_container_app" "server" {
  name                         = "banking-server"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"
  tags                         = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [module.identity.id]
  }

  # Pull images from ACR using the managed identity (no registry password).
  registry {
    server   = module.acr.login_server
    identity = module.identity.id
  }

  # Sensitive values live as ACA secrets, referenced by env below.
  secret {
    name  = "database-url"
    value = module.postgres.database_url
  }
  secret {
    name  = "plaid-client-id"
    value = var.plaid_client_id
  }
  secret {
    name  = "plaid-secret"
    value = var.plaid_secret
  }

  ingress {
    external_enabled = false # internal-only: only the ui app (same env) can reach it
    target_port      = 8787
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0 # scale-to-zero when idle; cold-starts on first request
    max_replicas = 1

    container {
      name   = "server"
      image  = "${module.acr.login_server}/banking-server:${var.server_image_tag}"
      cpu    = 0.5
      memory = "1Gi"

      # --- secrets ---
      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }
      env {
        name        = "PLAID_CLIENT_ID"
        secret_name = "plaid-client-id"
      }
      env {
        name        = "PLAID_SECRET"
        secret_name = "plaid-secret"
      }

      # --- plain config ---
      env {
        name  = "PLAID_ENV"
        value = var.plaid_env
      }
      env {
        name  = "SANDBOX_INSTITUTION_ID"
        value = var.sandbox_institution_id
      }
      env {
        name  = "LLM_PROVIDER"
        value = "foundry"
      }
      env {
        name  = "AGENT_BACKEND"
        value = var.agent_backend
      }
      env {
        name  = "AZURE_OPENAI_ENDPOINT"
        value = var.azure_openai_endpoint
      }
      env {
        name  = "AZURE_OPENAI_DEPLOYMENT"
        value = var.azure_openai_deployment
      }
      env {
        name  = "AZURE_OPENAI_API_VERSION"
        value = var.azure_openai_api_version
      }
      env {
        name  = "AZURE_AI_PROJECT_ENDPOINT"
        value = var.azure_ai_project_endpoint
      }

      # THE PHASE-C PAYOFF: point the app at the user-assigned MI. With only
      # AZURE_CLIENT_ID set (no SECRET, no TENANT), the credential ladder in
      # llm_client.py / foundry_agent.py falls through to DefaultAzureCredential,
      # which uses this client id to pick the managed identity. Zero secrets.
      env {
        name  = "AZURE_CLIENT_ID"
        value = module.identity.client_id
      }
    }
  }

  # Ensure AcrPull / Foundry roles exist before the app tries to pull + call.
  depends_on = [module.identity]
}

# ============================================================================
# ui — nginx serving React + proxying /api to the server's INTERNAL address.
# EXTERNAL ingress: this is the only public URL. This is the front door.
# ============================================================================
resource "azurerm_container_app" "ui" {
  name                         = "banking-ui"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"
  tags                         = var.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [module.identity.id]
  }

  # Easy Auth reads the app-registration client secret from this container app
  # secret (referenced by name in authConfigs — see auth.tf). Value comes from a
  # gitignored var (secrets.auto.tfvars) — the app registration is managed
  # out-of-band, so Terraform just consumes its secret here.
  secret {
    name  = "microsoft-provider-authentication-secret"
    value = var.easyauth_client_secret
  }

  registry {
    server   = module.acr.login_server
    identity = module.identity.id
  }

  ingress {
    external_enabled = true # public front door
    target_port      = 80
    transport        = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 0
    max_replicas = 1

    container {
      name   = "ui"
      image  = "${module.acr.login_server}/banking-ui:${var.ui_image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      # nginx.conf.template reads this at container start (envsubst) and proxies
      # /api → the server's internal HTTPS ingress. proxy_ssl + $proxy_host in
      # the template make the internal TLS + Host routing work.
      env {
        name  = "API_UPSTREAM"
        value = "https://${azurerm_container_app.server.ingress[0].fqdn}"
      }
    }
  }

  depends_on = [module.identity, azurerm_container_app.server]
}
