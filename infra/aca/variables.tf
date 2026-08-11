# ============================================================================
# Identity / placement
# ============================================================================
variable "subscription_id" {
  type        = string
  description = "MCAP subscription that hosts everything (and the Foundry resource)."
}

variable "location" {
  type    = string
  default = "canadacentral"
}

variable "resource_group_name" {
  type    = string
  default = "rg-banking-copilot-aca"
}

# Short suffix appended to globally-unique names (ACR, Postgres). Lowercase
# letters/digits only. Change if a name collides.
variable "name_suffix" {
  type    = string
  default = "bcaca1"
}

variable "tags" {
  type = map(string)
  default = {
    project = "banking-copilot"
    stage   = "7-aca"
    managed = "terraform"
  }
}

# ============================================================================
# Existing shared Log Analytics workspace (reused, not created)
# ============================================================================
variable "log_analytics_workspace_name" {
  type    = string
  default = "FPlogs01"
}

variable "log_analytics_resource_group_name" {
  type    = string
  default = "RG_Monitoring"
}

# ============================================================================
# Foundry resource (already exists — we only grant roles + point the app at it)
# ============================================================================
variable "foundry_resource_id" {
  type        = string
  description = "Resource ID of the existing Foundry / Cognitive Services account."
  default     = "/subscriptions/61c69764-de07-4358-beec-91174c9ab5c3/resourceGroups/RG_Plaidapp_testing/providers/Microsoft.CognitiveServices/accounts/plaid-app-testing-resource"
}

variable "azure_openai_endpoint" {
  type    = string
  default = "https://plaid-app-testing-resource.cognitiveservices.azure.com/"
}

variable "azure_openai_deployment" {
  type    = string
  default = "gpt-5.4-mini"
}

variable "azure_openai_api_version" {
  type    = string
  default = "2025-04-01-preview"
}

variable "azure_ai_project_endpoint" {
  type    = string
  default = "https://plaid-app-testing-resource.services.ai.azure.com/api/projects/plaid-app-testing"
}

variable "agent_backend" {
  type    = string
  default = "foundry"
}

# ============================================================================
# Stage 7.5 — APIM publisher metadata (required on every APIM instance)
# ============================================================================
variable "apim_publisher_name" {
  type    = string
  default = "Banking Copilot Lab"
}

variable "apim_publisher_email" {
  type    = string
  default = "amansahota@fargopost.com"
}

# ============================================================================
# Stage 7.5 — Easy Auth (banking-ui login)
# The Entra app registration is created OUT-OF-BAND (portal Easy Auth wizard or
# a directory admin) because ARM "Owner" can't write Entra objects. Terraform
# consumes its client id (non-secret → terraform.tfvars) and client secret
# (sensitive → gitignored secrets.auto.tfvars). See auth.tf for the full why.
# ============================================================================
variable "easyauth_client_id" {
  type        = string
  description = "Client (application) id of the Entra app registration behind banking-ui Easy Auth."
}

variable "easyauth_client_secret" {
  type        = string
  sensitive   = true
  description = "Client secret for the Easy Auth app registration. Provide via secrets.auto.tfvars."
}

# ============================================================================
# Images (filled after we push to ACR — build-push-images step)
# ============================================================================
variable "server_image_tag" {
  type        = string
  default     = "v1"
  description = "Tag for the banking-server image in ACR."
}

variable "ui_image_tag" {
  type        = string
  default     = "v1"
  description = "Tag for the banking-ui image in ACR."
}

# ============================================================================
# Secrets — DO NOT hardcode. Provide via a gitignored secrets.auto.tfvars or
# TF_VAR_* environment variables.
# ============================================================================
variable "postgres_admin_password" {
  type        = string
  sensitive   = true
  description = "Admin password for the Postgres flexible server."
}

variable "plaid_client_id" {
  type      = string
  sensitive = true
}

variable "plaid_secret" {
  type      = string
  sensitive = true
}

variable "plaid_env" {
  type    = string
  default = "sandbox"
}

variable "sandbox_institution_id" {
  type    = string
  default = "ins_109508"
}

variable "admin_ip_address" {
  type        = string
  default     = ""
  description = "Optional: your public IP, to allow direct psql access to Postgres."
}
