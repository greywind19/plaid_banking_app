# ============================================================================
# APIM module inputs
# ============================================================================
variable "name" {
  type        = string
  description = "Globally-unique APIM instance name (e.g. apim-banking-bcaca1)."
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

# Publisher identity is required metadata on every APIM instance (shows on the
# developer portal — hidden on Consumption — and in notification emails).
variable "publisher_name" {
  type    = string
  default = "Banking Copilot Lab"
}

variable "publisher_email" {
  type = string
}

variable "tags" {
  type    = map(string)
  default = {}
}
