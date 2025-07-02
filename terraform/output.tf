output "storage_account_name" {
  value = azurerm_storage_account.bdcc.name
}

output "databricks_workspace_name" {
  value = azurerm_databricks_workspace.bdcc.name
}

output "databricks_workspace_url" {
  value = azurerm_databricks_workspace.bdcc.workspace_url
}

output "databricks_cluster_name" {
  value = databricks_cluster.bdcc_cluster.cluster_name
}
