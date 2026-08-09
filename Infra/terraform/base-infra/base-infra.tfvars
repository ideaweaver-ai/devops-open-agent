# Terraform variable values for base-infra
# Set `s3_bucket_name` to a non-empty value to use the fixed backend state bucket.
# Set `artifact_bucket_name` to the fixed bucket name created by the base-infra module.

aws_region           = "us-east-1"
project              = "devops-openagent"
s3_bucket_name       = "devops-openagent-base"
artifact_bucket_name = "devops-openagent-state"
