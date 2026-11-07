resource "azurerm_resource_group" "finance" {
  name     = "acme-finance-rg"
  location = "Central India"
}

# Invoice archive shared through a public container.
resource "azurerm_storage_account" "invoices" {
  name                            = "acmeinvoicearchive"
  resource_group_name             = azurerm_resource_group.finance.name
  location                        = azurerm_resource_group.finance.location
  account_tier                    = "Standard"
  account_replication_type        = "LRS"
  min_tls_version                 = "TLS1_0"
  https_traffic_only_enabled      = false
  allow_nested_items_to_be_public = true
}

resource "azurerm_storage_container" "invoices" {
  name                  = "invoices"
  storage_account_id    = azurerm_storage_account.invoices.id
  container_access_type = "container"
}

resource "azurerm_network_security_group" "jumpbox" {
  name                = "acme-jumpbox-nsg"
  location            = azurerm_resource_group.finance.location
  resource_group_name = azurerm_resource_group.finance.name

  security_rule {
    name                       = "rdp-anywhere"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "3389"
    source_address_prefix      = "*"
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
  public_network_access_enabled = true
}

resource "azurerm_mssql_firewall_rule" "allow_all" {
  name             = "allow-all"
  server_id        = azurerm_mssql_server.finance.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "255.255.255.255"
}

resource "azurerm_key_vault" "finance" {
  name                     = "acme-finance-kv"
  location                 = azurerm_resource_group.finance.location
  resource_group_name      = azurerm_resource_group.finance.name
  tenant_id                = var.tenant_id
  sku_name                 = "standard"
  purge_protection_enabled = false
}

resource "azurerm_kubernetes_cluster" "analytics" {
  name                              = "acme-analytics-aks"
  location                          = azurerm_resource_group.finance.location
  resource_group_name               = azurerm_resource_group.finance.name
  dns_prefix                        = "acme-analytics"
  role_based_access_control_enabled = false

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
