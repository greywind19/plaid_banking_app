output "ui_url" {
  description = "Public URL of the app (open this in a browser)."
  value       = "https://${azurerm_container_app.ui.ingress[0].fqdn}"
}

output "server_internal_fqdn" {
  description = "Internal-only hostname the ui proxies to (not public)."
  value       = azurerm_container_app.server.ingress[0].fqdn
}

output "acr_login_server" {
  description = "Push images here: <this>/banking-server:TAG and /banking-ui:TAG."
  value       = module.acr.login_server
}

output "acr_name" {
  value = module.acr.name
}

output "postgres_fqdn" {
  value = module.postgres.fqdn
}

output "managed_identity_client_id" {
  value = module.identity.client_id
}

# ---- Stage 7.5: APIM -------------------------------------------------------
output "apim_name" {
  value = module.apim.name
}

output "apim_gateway_url" {
  description = "APIM gateway base URL. Step 2 points the server's AZURE_OPENAI_ENDPOINT here."
  value       = module.apim.gateway_url
}

output "apim_principal_id" {
  description = "APIM system MI principal — grant Cognitive Services User on Foundry in Step 2."
  value       = module.apim.principal_id
}

# ---- Stage 7.5: Easy Auth --------------------------------------------------
output "auth_app_client_id" {
  description = "Entra app registration (client) id behind banking-ui Easy Auth."
  value       = var.easyauth_client_id
}

