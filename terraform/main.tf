# Setup azurerm as a state backend
terraform {
  backend "azurerm" {
    subscription_id      = "454ff9db-a0ee-4017-a9e9-d51f663563e6"
    resource_group_name  = "test_group"
    storage_account_name = "mystorageaccount12311231" # Provide Storage Account name, where Terraform Remote state is stored
    container_name       = "terraform-state"
    key                  = "bdcc.tfstate"
  }
}

# Configure the Microsoft Azure Provider
provider "azurerm" {
  subscription_id = "454ff9db-a0ee-4017-a9e9-d51f663563e6"
  features {}
}

data "azurerm_client_config" "current" {}

resource "azurerm_resource_group" "bdcc" {
  name     = "rg-${var.ENV}-${var.LOCATION}"
  location = var.LOCATION

  lifecycle {
    # prevent_destroy = true
  }

  tags = {
    region = var.BDCC_REGION
    env    = var.ENV
  }
}

resource "azurerm_storage_account" "bdcc" {
  depends_on = [
  azurerm_resource_group.bdcc]

  name                     = "st${var.ENV}${var.LOCATION}"
  resource_group_name      = azurerm_resource_group.bdcc.name
  location                 = azurerm_resource_group.bdcc.location
  account_tier             = "Standard"
  account_replication_type = var.STORAGE_ACCOUNT_REPLICATION_TYPE
  is_hns_enabled           = "true"

  network_rules {
    default_action = "Allow"
    ip_rules       = values(var.IP_RULES)
  }

  lifecycle {
    # prevent_destroy = true
  }

  tags = {
    region = var.BDCC_REGION
    env    = var.ENV
  }
}

resource "azurerm_storage_data_lake_gen2_filesystem" "gen2_data" {
  depends_on = [
  azurerm_storage_account.bdcc]

  name               = "data"
  storage_account_id = azurerm_storage_account.bdcc.id

#  lifecycle {
#    prevent_destroy = true
#  }
}


resource "azurerm_kubernetes_cluster" "bdcc" {
  depends_on = [
  azurerm_resource_group.bdcc]

  name                = "aks-${var.ENV}-${var.LOCATION}"
  location            = azurerm_resource_group.bdcc.location
  resource_group_name = azurerm_resource_group.bdcc.name
  dns_prefix          = "bdcc${var.ENV}"

  default_node_pool {
    name       = "default"
    node_count = 1
    vm_size    = "Standard_B2s"
  }

  identity {
    type = "SystemAssigned"
  }

  tags = {
    region = var.BDCC_REGION
    env    = var.ENV
  }
}

resource "azurerm_container_registry" "acr" {
  name                = "marketplaceacr12311231"
  resource_group_name = azurerm_resource_group.bdcc.name
  location            = azurerm_resource_group.bdcc.location
  sku                 = "Basic"
  admin_enabled       = true

  tags = {
    region = var.BDCC_REGION
    env    = var.ENV
  }
}

resource "azurerm_role_assignment" "aks_acr_attach" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.bdcc.kubelet_identity[0].object_id
}

# New public IP in the managed resource group
resource "azurerm_public_ip" "ingress_ip" {
  name                = "ingress-ip"
  resource_group_name = var.aks_managed_resource_group
  location            = azurerm_resource_group.bdcc.location
  allocation_method   = "Static"
  sku                 = "Standard"
  tags = {
    region = var.BDCC_REGION
    env    = var.ENV
  }
}

# Role assignment updated to new public IP
resource "azurerm_role_assignment" "aks_ip_attach" {
  scope                = azurerm_public_ip.ingress_ip.id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_kubernetes_cluster.bdcc.identity[0].principal_id
}

# Grant AKS access to the storage account as Storage Blob Data Contributor
resource "azurerm_role_assignment" "aks_to_storage_blob" {
  scope                = azurerm_storage_account.bdcc.id  
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_kubernetes_cluster.bdcc.identity[0].principal_id
}

# Output updated
output "ingress_ip" {
  value = azurerm_public_ip.ingress_ip.ip_address
}

output "client_certificate" {
  sensitive = true
  value = azurerm_kubernetes_cluster.bdcc.kube_config.0.client_certificate
}

output "kube_config" {
  sensitive = true
  value     = azurerm_kubernetes_cluster.bdcc.kube_config_raw
}

output "acr_name" {
  value = azurerm_container_registry.acr.name
}

provider "databricks" {
  host                        = azurerm_databricks_workspace.bdcc.workspace_url
  azure_workspace_resource_id = azurerm_databricks_workspace.bdcc.id
}

resource "azurerm_databricks_workspace" "bdcc" {
  depends_on = [
    azurerm_resource_group.bdcc
  ]

  name                = "dbw-${var.ENV}-${var.LOCATION}"
  resource_group_name = azurerm_resource_group.bdcc.name
  location            = azurerm_resource_group.bdcc.location
  sku                 = "standard"

  tags = {
    region = var.BDCC_REGION
    env    = var.ENV
  }
}

resource "databricks_cluster" "bdcc_cluster" {
  depends_on              = [azurerm_databricks_workspace.bdcc]
  cluster_name            = "bdcc-cluster"
  spark_version           = "15.4.x-scala2.12"
  node_type_id            = "Standard_D4ds_v5"
  autotermination_minutes = 90
  num_workers             = 1
}
