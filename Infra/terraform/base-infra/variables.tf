variable "aws_region" {
  description = "AWS region to deploy resources into"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name prefix for resources"
  type        = string
  default     = "devops-openagent"
}

variable "s3_bucket_name" {
  description = "Explicit S3 bucket name for Terraform backend state"
  type        = string
  default     = "devops-openagent-base"
}

variable "artifact_bucket_name" {
  description = "Name of the S3 bucket created by the base-infra module for artifacts"
  type        = string
  default     = "devops-openagent-state"
}
