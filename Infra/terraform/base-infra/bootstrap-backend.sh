#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<EOF
Usage: $0 [-var-file PATH]

This script bootstraps the Terraform backend for base-infra by ensuring the
required S3 bucket and DynamoDB lock table exist before Terraform init.

Options:
  -var-file PATH  Path to the Terraform variables file (default: base-infra.tfvars)
EOF
  exit 1
}

TFVARS_FILE="base-infra.tfvars"
while [[ $# -gt 0 ]]; do
  case "$1" in
    -var-file)
      shift
      if [[ $# -eq 0 ]]; then
        echo "Missing value for -var-file" >&2
        usage
      fi
      TFVARS_FILE="$1"
      shift
      ;;
    -var-file=*)
      TFVARS_FILE="${1#-var-file=}"
      shift
      ;;
    --var-file)
      shift
      if [[ $# -eq 0 ]]; then
        echo "Missing value for --var-file" >&2
        usage
      fi
      TFVARS_FILE="$1"
      shift
      ;;
    --var-file=*)
      TFVARS_FILE="${1#--var-file=}"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage
      ;;
  esac
done

parse_tfvar() {
  local key="$1"
  grep -E "^${key}[[:space:]]*=" "$TFVARS_FILE" | head -n 1 | sed -E 's/^.+=[[:space:]]*//; s/[" ]//g'
}

AWS_REGION="${AWS_REGION:-$(parse_tfvar aws_region)}"
# The backend state bucket is created by this script and should match
# the Terraform backend bucket configured in provider.tf.
S3_BUCKET_NAME="${S3_BUCKET_NAME:-$(parse_tfvar s3_bucket_name)}"
PROJECT_NAME="${PROJECT_NAME:-$(parse_tfvar project)}"

if [[ -z "$AWS_REGION" || -z "$S3_BUCKET_NAME" || -z "$PROJECT_NAME" ]]; then
  echo "Failed to parse required backend variables from $TFVARS_FILE" >&2
  echo "Parsed values: AWS_REGION='$AWS_REGION', S3_BUCKET_NAME='$S3_BUCKET_NAME', PROJECT_NAME='$PROJECT_NAME'" >&2
  exit 1
fi

if ! command -v aws >/dev/null 2>&1; then
  echo "AWS CLI is required to bootstrap the Terraform backend. Install it and retry." >&2
  exit 1
fi

export AWS_REGION="$AWS_REGION"
export AWS_DEFAULT_REGION="$AWS_REGION"

# The backend lock table for bootstrap is distinct from the base infra module table.
DYNAMODB_TABLE_NAME="devops0-openagent-base"

# Ensure bucket exists
if aws s3api head-bucket --bucket "$S3_BUCKET_NAME" >/dev/null 2>&1; then
  echo "S3 bucket '$S3_BUCKET_NAME' already exists."
else
  echo "Creating S3 bucket '$S3_BUCKET_NAME' in region '$AWS_REGION'..."
  if [[ "$AWS_REGION" == "us-east-1" ]]; then
    aws s3api create-bucket --bucket "$S3_BUCKET_NAME" --region "$AWS_REGION" >/dev/null
  else
    aws s3api create-bucket --bucket "$S3_BUCKET_NAME" --region "$AWS_REGION" --create-bucket-configuration LocationConstraint="$AWS_REGION" >/dev/null
  fi
  echo "Created S3 bucket '$S3_BUCKET_NAME'."
fi

# Ensure DynamoDB table exists
if aws dynamodb describe-table --table-name "$DYNAMODB_TABLE_NAME" >/dev/null 2>&1; then
  echo "DynamoDB table '$DYNAMODB_TABLE_NAME' already exists."
else
  echo "Creating DynamoDB table '$DYNAMODB_TABLE_NAME'..."
  aws dynamodb create-table \
    --table-name "$DYNAMODB_TABLE_NAME" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --tags Key=Project,Value="$PROJECT_NAME" >/dev/null
  echo "Waiting for DynamoDB table '$DYNAMODB_TABLE_NAME' to become active..."
  aws dynamodb wait table-exists --table-name "$DYNAMODB_TABLE_NAME"
  echo "Created DynamoDB table '$DYNAMODB_TABLE_NAME'."
fi

echo "Backend bootstrap complete."
