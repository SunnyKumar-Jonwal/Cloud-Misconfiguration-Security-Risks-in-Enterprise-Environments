# Acme Retail (fictional) - the hardened estate after four unreviewed changes made directly
# in production and later imported into Terraform. Used to demonstrate drift detection.
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
