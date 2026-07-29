terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.100"
    }
  }

  # ---- STATE BACKEND -------------------------------------------------------
  # Starts LOCAL (terraform.tfstate on disk, gitignored). To migrate to Azure
  # Storage later: create a storage account + container, uncomment this block,
  # fill the names, then run `terraform init -migrate-state`. Terraform copies
  # the existing local state into the blob — no resources are recreated.
  #
  # backend "azurerm" {
  #   resource_group_name  = "rg-tfstate"
  #   storage_account_name = "sttfstatebankingcopilot"
  #   container_name       = "tfstate"
  #   key                  = "aca.terraform.tfstate"
  # }
}

provider "azurerm" {
  features {}

  # Pin to the MCAP subscription (same tenant as the Foundry resource, so the
  # managed identity is single-tenant and can call Foundry with no cross-tenant
  # hassle). Overridable via var if you ever retarget.
  subscription_id = var.subscription_id
}
