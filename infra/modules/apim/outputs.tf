output "id" {
  value = azurerm_api_management.this.id
}

output "name" {
  value = azurerm_api_management.this.name
}

# The base URL clients hit. In Step 2 the server's AZURE_OPENAI_ENDPOINT points
# here instead of directly at the Foundry resource.
output "gateway_url" {
  value = azurerm_api_management.this.gateway_url
}

# APIM's system-assigned MI principal — granted "Cognitive Services User" on the
# Foundry resource in Step 2 so authentication-managed-identity policy works.
output "principal_id" {
  value = azurerm_api_management.this.identity[0].principal_id
}
