output "id" {
  description = "Resource ID of the managed identity (for container_app.identity)."
  value       = azurerm_user_assigned_identity.this.id
}

output "client_id" {
  description = "Client ID — pass to the app as AZURE_CLIENT_ID so the MI is selected."
  value       = azurerm_user_assigned_identity.this.client_id
}

output "principal_id" {
  value = azurerm_user_assigned_identity.this.principal_id
}
