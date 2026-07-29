# Azure Database for PostgreSQL — Flexible Server (managed).
# Replaces the local `postgres` container + pgdata volume. Automated backups,
# its own hostname, survives everything. B1ms burstable = cheapest tier.
resource "azurerm_postgresql_flexible_server" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location

  version                       = "16"
  administrator_login           = var.administrator_login
  administrator_password        = var.administrator_password
  storage_mb                    = 32768
  sku_name                      = "B_Standard_B1ms"
  public_network_access_enabled = true

  # No high-availability / zone pinning for a lab (keeps it cheap + simple).
  zone = "1"

  tags = var.tags

  lifecycle {
    # Azure sometimes returns a different zone than requested; don't churn.
    ignore_changes = [zone]
  }
}

# The application database.
resource "azurerm_postgresql_flexible_server_database" "banking" {
  name      = var.database_name
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# Firewall: allow other Azure services (the special 0.0.0.0 rule). This lets
# the ACA container reach the DB without static outbound IPs. For production
# you'd use a private endpoint / VNet integration instead.
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_azure" {
  name             = "AllowAzureServices"
  server_id        = azurerm_postgresql_flexible_server.this.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "0.0.0.0"
}

# Optional: allow your own IP so you can psql in to inspect (admin/debug).
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_admin_ip" {
  count            = var.admin_ip_address == "" ? 0 : 1
  name             = "AllowAdminIP"
  server_id        = azurerm_postgresql_flexible_server.this.id
  start_ip_address = var.admin_ip_address
  end_ip_address   = var.admin_ip_address
}
