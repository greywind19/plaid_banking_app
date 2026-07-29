output "id" {
  value = azurerm_container_registry.this.id
}

output "login_server" {
  description = "e.g. myregistry.azurecr.io — prefix for image names."
  value       = azurerm_container_registry.this.login_server
}

output "name" {
  value = azurerm_container_registry.this.name
}
