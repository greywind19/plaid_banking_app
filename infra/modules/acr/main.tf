# Azure Container Registry — hosts the server + ui images that ACA pulls.
# Basic SKU is the cheapest and plenty for a lab (10 GiB, one region).
resource "azurerm_container_registry" "this" {
  name                = var.name
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = "Basic"

  # Keep the admin user OFF — ACA pulls with the managed identity instead
  # (see the identity module + AcrPull role assignment). No passwords to leak.
  admin_enabled = false

  tags = var.tags
}
