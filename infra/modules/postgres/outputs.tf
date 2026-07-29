output "fqdn" {
  description = "Server hostname, e.g. myserver.postgres.database.azure.com"
  value       = azurerm_postgresql_flexible_server.this.fqdn
}

output "administrator_login" {
  value = azurerm_postgresql_flexible_server.this.administrator_login
}

output "database_name" {
  value = azurerm_postgresql_flexible_server_database.banking.name
}

# Ready-to-use SQLAlchemy URL for the app's token_store. sslmode=require is
# mandatory on Flexible Server. Marked sensitive because it embeds the password.
output "database_url" {
  sensitive = true
  value = format(
    "postgresql+psycopg://%s:%s@%s:5432/%s?sslmode=require",
    azurerm_postgresql_flexible_server.this.administrator_login,
    var.administrator_password,
    azurerm_postgresql_flexible_server.this.fqdn,
    azurerm_postgresql_flexible_server_database.banking.name,
  )
}
