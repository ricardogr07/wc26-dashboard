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

  template_content = jsonencode({
    "$schema"      = "https://schema.management.azure.com/schemas/2019-04-01/deploymentTemplate.json#"
    contentVersion = "1.0.0.0"
    parameters = {
      storageAccountName      = { type = "string" }
      storageConnectionString = { type = "securestring" }
      servicePlanId           = { type = "string" }
      cosmosConnectionString  = { type = "securestring" }
      cosmosDatabaseName      = { type = "string" }
      thesportsdbApiKey       = { type = "securestring" }
      corsOrigin              = { type = "string" }
      location                = { type = "string" }
      functionAppName         = { type = "string" }
    }
    resources = [
      {
        type       = "Microsoft.Storage/storageAccounts/blobServices/containers"
        apiVersion = "2023-01-01"
        name       = "[concat(parameters('storageAccountName'), '/default/deploymentpackages')]"
        properties = {}
      },
      {
        type       = "Microsoft.Web/sites"
        apiVersion = "2023-12-01"
        name       = "[parameters('functionAppName')]"
        location   = "[parameters('location')]"
        kind       = "functionapp,linux"
        dependsOn = [
          "[resourceId('Microsoft.Storage/storageAccounts/blobServices/containers', parameters('storageAccountName'), 'default', 'deploymentpackages')]"
        ]
        properties = {
          serverFarmId = "[parameters('servicePlanId')]"
          functionAppConfig = {
            deployment = {
              storage = {
                type  = "blobContainer"
                value = "[concat('https://', parameters('storageAccountName'), '.blob.core.windows.net/deploymentpackages')]"
                authentication = {
                  type                               = "StorageAccountConnectionString"
                  storageAccountConnectionStringName = "DEPLOYMENT_STORAGE_CONNECTION_STRING"
                }
              }
            }
            scaleAndConcurrency = {
              maximumInstanceCount = 100
              instanceMemoryMB     = 2048
            }
            runtime = {
              name    = "python"
              version = "3.11"
            }
          }
          siteConfig = {
            appSettings = [
              { name = "DEPLOYMENT_STORAGE_CONNECTION_STRING", value = "[parameters('storageConnectionString')]" },
              { name = "AzureWebJobsStorage",                  value = "[parameters('storageConnectionString')]" },
              { name = "COSMOS_CONNECTION_STRING",             value = "[parameters('cosmosConnectionString')]" },
              { name = "COSMOS_DATABASE_NAME",                 value = "[parameters('cosmosDatabaseName')]" },
              { name = "COSMOS_CONTAINER_NAME",                value = "items" },
              { name = "THESPORTSDB_API_KEY",                  value = "[parameters('thesportsdbApiKey')]" },
              { name = "SYNC_INTERVAL_HOURS",                  value = "1" },
              { name = "AzureWebJobsFeatureFlags",             value = "EnableWorkerIndexing" }
            ]
            cors = {
              allowedOrigins = ["[parameters('corsOrigin')]"]
            }
          }
        }
      }
    ]
    outputs = {
      functionAppHostname = {
        type  = "string"
        value = "[reference(parameters('functionAppName')).defaultHostName]"
      }
    }
  })

  parameters_content = jsonencode({
    storageAccountName      = { value = azurerm_storage_account.functions.name }
    storageConnectionString = { value = azurerm_storage_account.functions.primary_connection_string }
    servicePlanId           = { value = azurerm_service_plan.consumption.id }
    cosmosConnectionString  = { value = azurerm_cosmosdb_account.main.primary_sql_connection_string }
    cosmosDatabaseName      = { value = var.cosmos_database_name }
    thesportsdbApiKey       = { value = var.thesportsdb_api_key }
    corsOrigin              = { value = "https://${azurerm_static_web_app.frontend.default_host_name}" }
    location                = { value = azurerm_resource_group.main.location }
    functionAppName         = { value = var.function_app_name }
  })
}
