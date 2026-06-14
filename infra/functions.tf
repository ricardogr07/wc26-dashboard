resource "random_string" "storage_suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_storage_account" "functions" {
  name                     = "wc26fn${random_string.storage_suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  tags = local.tags
}

resource "azurerm_service_plan" "consumption" {
  name                = "${local.prefix}-consumption-plan"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "FC1"

  tags = local.tags
}

# azurerm 3.x cannot create a function app on FC1 (Flex Consumption) because
# the provider omits the `functionAppConfig` property required by the Azure API.
# We use a raw ARM deployment to work around this.
resource "azurerm_resource_group_template_deployment" "function_app" {
  name                = "wc26-api-deployment"
  resource_group_name = azurerm_resource_group.main.name
  deployment_mode     = "Incremental"

  template_content = file("${path.module}/arm/function_app.json")

  parameters_content = jsonencode({
    storageAccountName      = { value = azurerm_storage_account.functions.name }
    storageConnectionString = { value = azurerm_storage_account.functions.primary_connection_string }
    servicePlanId           = { value = azurerm_service_plan.consumption.id }
    cosmosConnectionString  = { value = azurerm_cosmosdb_account.main.primary_sql_connection_string }
    cosmosDatabaseName      = { value = var.cosmos_database_name }
    thesportsdbApiKey       = { value = var.thesportsdb_api_key }
    thesportsdbLeagueId     = { value = var.thesportsdb_league_id }
    thesportsdbSeason       = { value = var.thesportsdb_season }
    timerSchedule           = { value = var.timer_schedule }
    corsOrigin              = { value = "https://${azurerm_static_web_app.frontend.default_host_name}" }
    location                = { value = azurerm_resource_group.main.location }
    functionAppName         = { value = var.function_app_name }
  })
}
