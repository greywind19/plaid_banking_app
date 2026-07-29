variable "name" {
  type        = string
  description = "Name for the user-assigned managed identity."
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "subscription_id" {
  type        = string
  description = "Subscription ID hosting the Foundry resource (for the role-definition path)."
}

variable "acr_id" {
  type        = string
  description = "Resource ID of the ACR to grant AcrPull on."
}

variable "foundry_resource_id" {
  type        = string
  description = "Resource ID of the Foundry / Cognitive Services account to grant model + agent roles on."
}

variable "tags" {
  type    = map(string)
  default = {}
}
