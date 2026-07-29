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
