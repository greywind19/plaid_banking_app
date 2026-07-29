variable "name" {
  type        = string
  description = "Globally-unique flexible server name (lowercase, 3-63 chars)."
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

variable "administrator_login" {
  type    = string
  default = "banking"
}

variable "administrator_password" {
  type        = string
  sensitive   = true
  description = "Postgres admin password (>= 8 chars, 3 of upper/lower/digit/special)."
}

variable "database_name" {
  type    = string
  default = "banking"
}

variable "admin_ip_address" {
  type        = string
  default     = ""
  description = "Optional public IP to allow for direct psql access. Empty = skip."
}

variable "tags" {
  type    = map(string)
  default = {}
}
