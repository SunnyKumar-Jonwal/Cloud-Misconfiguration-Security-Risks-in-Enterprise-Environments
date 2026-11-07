# Acme Retail (fictional) - hardened version of the vulnerable estate: every finding fixed.
# Each change is the remediation suggested by the corresponding CloudGuard rule.
# DO NOT DEPLOY.

terraform {
  required_providers {
    aws     = { source = "hashicorp/aws", version = "~> 5.0" }
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
  }
}

provider "aws" {
  region = "ap-south-1"
}

provider "azurerm" {
  features {}
}
