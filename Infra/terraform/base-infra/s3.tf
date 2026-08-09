resource "aws_s3_bucket" "artifact_bucket" {
  # Use a deterministic bucket name supplied by variable `artifact_bucket_name`.
  # This bucket is separate from the Terraform backend state bucket, which is
  # bootstrapped as `devops-openagent-base`.
  bucket        = var.artifact_bucket_name
  force_destroy = false

  tags = {
    Name    = "${var.project}-artifacts"
    Project = var.project
  }
}

resource "aws_s3_bucket_versioning" "artifact_bucket" {
  bucket = aws_s3_bucket.artifact_bucket.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "artifact_bucket" {
  bucket = aws_s3_bucket.artifact_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "block" {
  bucket = aws_s3_bucket.artifact_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
