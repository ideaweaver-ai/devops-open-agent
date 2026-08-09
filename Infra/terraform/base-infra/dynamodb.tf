resource "aws_dynamodb_table" "lock_files" {
  name     = "${var.project}-lock-files"
  hash_key = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  billing_mode = "PAY_PER_REQUEST"

  tags = {
    Name    = "Lock-Files"
    Project = var.project
  }
}
