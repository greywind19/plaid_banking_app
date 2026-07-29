# User-assigned Managed Identity for the server Container App.
# This is what replaces the service-principal client-secret from Stage 6.
# Azure hands this identity tokens automatically inside ACA, so the app's
# DefaultAzureCredential branch just works — zero secrets in the cloud.
resource "azurerm_user_assigned_identity" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

# ---- Role 1: pull images from ACR --------------------------------------
resource "azurerm_role_assignment" "acr_pull" {
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}

# ---- Role 2: call the model (inference / Azure OpenAI data plane) -------
resource "azurerm_role_assignment" "openai_user" {
  scope                = var.foundry_resource_id
  role_definition_name = "Cognitive Services OpenAI User"
  principal_id         = azurerm_user_assigned_identity.this.principal_id
}

# ---- Role 3: Foundry Agent Service data plane (Threads + Runs) ----------
# "Azure AI Developer" / "Foundry User" — assigned by its role definition ID
# because the display name varies by tenant. GUID 53ca6127 is the one we
# already granted the Stage 6 service principal.
resource "azurerm_role_assignment" "foundry_user" {
  scope              = var.foundry_resource_id
  role_definition_id = "/subscriptions/${var.subscription_id}/providers/Microsoft.Authorization/roleDefinitions/53ca6127-db72-4b80-b1b0-d745d6d5456d"
  principal_id       = azurerm_user_assigned_identity.this.principal_id
}
