output "s3_bucket_name" {
  description = "Name of the S3 bucket created for artifacts"
  value       = aws_s3_bucket.artifact_bucket.bucket
}

output "s3_bucket_arn" {
  description = "ARN of the S3 bucket"
  value       = aws_s3_bucket.artifact_bucket.arn
}

output "dynamodb_table_name" {
  description = "DynamoDB table name for lock files"
  value       = aws_dynamodb_table.lock_files.name
}

output "dynamodb_table_arn" {
  description = "DynamoDB table ARN"
  value       = aws_dynamodb_table.lock_files.arn
}

output "aws_region" {
  description = "AWS region used for deployment"
  value       = var.aws_region
}

output "s3_console_url" {
  description = "AWS Console URL to view the S3 bucket"
  value       = "https://s3.console.aws.amazon.com/s3/buckets/${aws_s3_bucket.artifact_bucket.bucket}?region=${var.aws_region}&tab=objects"
}

output "dynamodb_console_url" {
  description = "AWS Console URL to view the DynamoDB table"
  value       = "https://console.aws.amazon.com/dynamodbv2/home?region=${var.aws_region}#table?name=${aws_dynamodb_table.lock_files.name}"
}
