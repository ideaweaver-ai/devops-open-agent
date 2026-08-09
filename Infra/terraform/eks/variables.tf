variable "aws-region" {}
variable "env" {}
variable "cluster-name" {}
variable "vpc-cidr-block" {}
variable "vpc-name" {}
variable "igw-name" {}
variable "pub-subnet-count" {}
variable "pub-cidr-block" {
  type = list(string)
}
variable "pub-availability-zone" {
  type = list(string)
}
variable "pub-sub-name" {}
variable "pri-subnet-count" {}
variable "pri-cidr-block" {
  type = list(string)
}
variable "pri-availability-zone" {
  type = list(string)
}
variable "pri-sub-name" {}
variable "public-rt-name" {}
variable "private-rt-name" {}
variable "eip-name" {}
variable "ngw-name" {}
variable "eks-sg" {}


# EKS
variable "is-eks-cluster-enabled" {}
variable "cluster-version" {}
variable "endpoint-private-access" {}
variable "endpoint-public-access" {}
variable "ondemand_instance_types" {
  default = ["t3a.medium"]
}

variable "spot_instance_types" {}
variable "desired_capacity_on_demand" {}
variable "min_capacity_on_demand" {}
variable "max_capacity_on_demand" {}
variable "desired_capacity_spot" {}
variable "min_capacity_spot" {}
variable "max_capacity_spot" {}
variable "addons" {
  type = list(object({
    name    = string
    version = string
  }))
}

variable "base_infra_s3_bucket_name" {
  description = "Static S3 bucket name used for base infra state and artifacts"
  type        = string
  default     = "devops-openagent-state"
}

variable "base_infra_dynamodb_table_name" {
  description = "Static DynamoDB table name used for base infra state locking"
  type        = string
  default     = "devops-openagent-lock-files"
}

variable "create_bastion" {
  type    = bool
  default = true
}

variable "bastion_instance_type" {
  type    = string
  default = "t2.medium"
}

variable "bastion_public_subnet_index" {
  type    = number
  default = 0
}

variable "bastion_allowed_cidr_blocks" {
  description = "CIDR blocks allowed to SSH to the bastion host"
  type        = list(string)
}