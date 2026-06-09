output "function_app_name" {
  description = "Name of the Azure Function App"
  value       = azurerm_linux_function_app.api.name
}

output "function_app_url" {
  description = "Default hostname of the Azure Function App"
  value       = "https://${azurerm_linux_function_app.api.default_hostname}"
}

output "static_web_app_url" {
  description = "Default hostname of the Static Web App"
  value       = "https://${azurerm_static_web_app.frontend.default_host_name}"
}

output "static_web_app_deployment_token" {
  description = "Deployment token for the Static Web App (used by GitHub Actions)"
  value       = azurerm_static_web_app.frontend.api_key
  sensitive   = true
}

output "cosmos_endpoint" {
  description = "Cosmos DB endpoint URL"
  value       = azurerm_cosmosdb_account.main.endpoint
}

output "cosmos_connection_string" {
  description = "Cosmos DB primary connection string"
  value       = azurerm_cosmosdb_account.main.primary_sql_connection_string
  sensitive   = true
}
