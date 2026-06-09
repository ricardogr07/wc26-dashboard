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
  sku_name            = "Y1"

  tags = local.tags
}

resource "azurerm_linux_function_app" "api" {
  name                = var.function_app_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  storage_account_name       = azurerm_storage_account.functions.name
  storage_account_access_key = azurerm_storage_account.functions.primary_access_key
  service_plan_id            = azurerm_service_plan.consumption.id

  site_config {
    application_stack {
      python_version = "3.11"
    }
    cors {
      allowed_origins = [
        "https://${azurerm_static_web_app.frontend.default_host_name}",
      ]
    }
  }

  app_settings = {
    COSMOS_CONNECTION_STRING = azurerm_cosmosdb_account.main.primary_sql_connection_string
    COSMOS_DATABASE_NAME     = var.cosmos_database_name
    COSMOS_CONTAINER_NAME    = "items"
    THESPORTSDB_API_KEY      = var.thesportsdb_api_key
    SYNC_INTERVAL_HOURS      = "1"
    FUNCTIONS_WORKER_RUNTIME = "python"
    AzureWebJobsFeatureFlags = "EnableWorkerIndexing"
  }

  tags = local.tags
}
