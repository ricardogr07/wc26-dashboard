variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "eastus2"
}

variable "resource_group_name" {
  description = "Name of the main resource group"
  type        = string
  default     = "wc26-dashboard-rg"
}

variable "cosmos_account_name" {
  description = "Cosmos DB account name (must be globally unique)"
  type        = string
  default     = "wc26-cosmos"
}

variable "cosmos_database_name" {
  description = "Cosmos DB database name"
  type        = string
  default     = "wc26db"
}

variable "function_app_name" {
  description = "Azure Function App name (must be globally unique)"
  type        = string
  default     = "wc26-api"
}

variable "static_web_app_name" {
  description = "Azure Static Web App name"
  type        = string
  default     = "wc26-dashboard"
}

variable "thesportsdb_api_key" {
  description = "TheSportsDB API key"
  type        = string
  sensitive   = true
}

variable "thesportsdb_league_id" {
  description = "TheSportsDB league ID for the FIFA World Cup 2026"
  type        = string
  default     = "4429"
}

variable "thesportsdb_season" {
  description = "TheSportsDB season string for WC 2026"
  type        = string
  default     = "2026-2027"
}

variable "timer_schedule" {
  description = "NCRONTAB schedule for the sync_matches timer trigger (six-field format)"
  type        = string
  default     = "0 */2 * * * *"
}

variable "cosmos_free_tier" {
  description = "Enable Cosmos DB free tier (only one per subscription)"
  type        = bool
  default     = true
}
