resource "azurerm_resource_group" "finance" {
  name     = "acme-finance-rg"
  location = "Central India"
}

resource "azurerm_storage_account" "invoices" {
  name                            = "acmeinvoicearchive"
  resource_group_name             = azurerm_resource_group.finance.name
  location                        = azurerm_resource_group.finance.location
  account_tier                    = "Standard"
  account_replication_type        = "GRS"
  min_tls_version                 = "TLS1_2"
  https_traffic_only_enabled      = true
  allow_nested_items_to_be_public = false
}

resource "azurerm_storage_container" "invoices" {
  name                  = "invoices"
  storage_account_id    = azurerm_storage_account.invoices.id
  container_access_type = "private"
}

# Remote administration through Azure Bastion from the corporate range only.
resource "azurerm_network_security_group" "jumpbox" {
  name                = "acme-jumpbox-nsg"
  location            = azurerm_resource_group.finance.location
  resource_group_name = azurerm_resource_group.finance.name

  security_rule {
    name                       = "rdp-from-bastion"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3389"
    source_address_prefix      = "10.50.0.0/26"
    destination_address_prefix = "*"
  }
}

resource "azurerm_mssql_server" "finance" {
  name                          = "acme-finance-sql"
  resource_group_name           = azurerm_resource_group.finance.name
  location                      = azurerm_resource_group.finance.location
  version                       = "12.0"
  administrator_login           = "sqladmin"
  administrator_login_password  = var.sql_admin_password
  public_network_access_enabled = false
}

resource "azurerm_key_vault" "finance" {
  name                     = "acme-finance-kv"
  location                 = azurerm_resource_group.finance.location
  resource_group_name      = azurerm_resource_group.finance.name
  tenant_id                = var.tenant_id
  sku_name                 = "standard"
  purge_protection_enabled = true
}

resource "azurerm_kubernetes_cluster" "analytics" {
  name                              = "acme-analytics-aks"
  location                          = azurerm_resource_group.finance.location
  resource_group_name               = azurerm_resource_group.finance.name
  dns_prefix                        = "acme-analytics"
  private_cluster_enabled           = true
  role_based_access_control_enabled = true

  default_node_pool {
    name       = "default"
    node_count = 2
    vm_size    = "Standard_D2s_v5"
  }

  identity {
    type = "SystemAssigned"
  }
}

variable "sql_admin_password" {
  type      = string
  sensitive = true
}

variable "tenant_id" {
  type = string
}
