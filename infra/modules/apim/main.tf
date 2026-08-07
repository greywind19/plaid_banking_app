# ============================================================================
# Azure API Management — Consumption tier, as an AI Gateway in front of Foundry.
# Consumption ("Consumption_0"): serverless, scale-to-zero (~$0 idle), all
# policies supported, provisions in minutes. Trade-offs vs Developer: no dev
# portal, no built-in cache, App Insights (not Log Analytics) request logs,
# cold-start after idle, best-effort (not dedicated) rate counters — none of
# which matter for a single-user learning lab.
# ============================================================================
resource "azurerm_api_management" "this" {
  name                = var.name
  location            = var.location
  resource_group_name = var.resource_group_name

  publisher_name  = var.publisher_name
  publisher_email = var.publisher_email

  sku_name = "Consumption_0"

  # System-assigned managed identity: this is what authenticates keylessly to
  # Azure OpenAI in Step 2 (granted "Cognitive Services User" on the Foundry
  # resource). No keys ever stored in APIM.
  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}
