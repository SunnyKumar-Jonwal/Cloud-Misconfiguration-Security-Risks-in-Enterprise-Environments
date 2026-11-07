# Acme Retail (fictional) - deliberately vulnerable estate used to evaluate CloudGuard.
# Every misconfiguration here mirrors a pattern from a real incident in Chapter 4.
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
