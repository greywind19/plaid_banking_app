# ============================================================================
# Stage 7.5 - User login (Easy Auth) codified
# ----------------------------------------------------------------------------
# Easy Auth needs two things: (1) an Entra APP REGISTRATION, and (2) a Container
# App `authConfigs/current` sub-resource that points at it.
#
# IMPORTANT - why the app registration is NOT managed here:
# App registrations live in Entra ID, and creating/updating them (adding a
# client secret, owners, etc.) requires an Entra DIRECTORY role such as
# Application Administrator. Subscription "Owner" (ARM RBAC) does NOT grant that
# - so this project''s identity gets a 403 from Microsoft Graph. The portal''s
# Easy Auth wizard can create the app because it runs an elevated auto-provision
# flow on your behalf; plain Terraform can''t.
#
# So we treat the app registration as an OUT-OF-BAND prerequisite: create it via
# the portal (Container App -> Authentication -> add Microsoft provider) or have
# a directory admin run a separate azuread config, then feed its client id +
# secret in as variables. Terraform still fully owns the ARM side - the
# container-app secret and the authConfig wiring below - which is what makes the
# app-infra reproducible.
#
# A fork/redeploy does the same: stand up an app registration, then set
# easyauth_client_id (tfvars) and easyauth_client_secret (secrets.auto.tfvars).
# ============================================================================

# Tenant id for the OIDC issuer (from azurerm - no extra provider needed).
data "azurerm_client_config" "current" {}

# ---- Turn on Easy Auth on banking-ui --------------------------------------
# authConfigs/current is a child of the container app. azapi PUTs the ARM body
# directly (azurerm''s azurerm_container_app has no auth block). The client
# secret is read from the container app secret of the same name, which is
# defined on azurerm_container_app.ui (see main.tf) from var.easyauth_client_secret.
resource "azapi_resource" "ui_auth" {
  type      = "Microsoft.App/containerApps/authConfigs@2024-03-01"
  name      = "current"
  parent_id = azurerm_container_app.ui.id

  body = jsonencode({
    properties = {
      platform = {
        enabled = true
      }
      globalValidation = {
        unauthenticatedClientAction = "RedirectToLoginPage"
        redirectToProvider          = "azureactivedirectory"
      }
      identityProviders = {
        azureActiveDirectory = {
          registration = {
            openIdIssuer            = "https://sts.windows.net/${data.azurerm_client_config.current.tenant_id}/v2.0"
            clientId                = var.easyauth_client_id
            clientSecretSettingName = "microsoft-provider-authentication-secret"
          }
          validation = {
            allowedAudiences = ["api://${var.easyauth_client_id}"]
            defaultAuthorizationPolicy = {
              allowedApplications = [var.easyauth_client_id]
            }
          }
        }
      }
    }
  })
}