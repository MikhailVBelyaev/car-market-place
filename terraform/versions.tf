terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>4.3.0"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.22.0"  # Adjust this to the latest version
    }
  }
}
