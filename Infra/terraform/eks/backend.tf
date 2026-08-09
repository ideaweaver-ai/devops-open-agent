terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.49.0"
    }
  }
  backend "s3" {
    bucket         = "devops-openagent-state"
    region         = "us-east-1"
    key            = "eks/terraform.tfstate"
    dynamodb_table = "devops-openagent-lock-files"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws-region
}