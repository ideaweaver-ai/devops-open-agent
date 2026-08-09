terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0.0"
    }
  }

  backend "s3" {
    bucket         = "devops-openagent-base"
    key            = "base-infra/terraform.tfstate"
    region         = "us-east-1"
    dynamodb_table = "devops0-openagent-base"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region
  # Credentials are picked up from the environment or shared config (~/.aws/credentials).
}
