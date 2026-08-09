variable "cluster-name" {}
variable "cidr-block" {}
variable "vpc-name" {}
variable "env" {}
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

variable "base_infra_s3_bucket_name" {
  type = string
}

variable "base_infra_dynamodb_table_name" {
  type = string
}

# Bastion host configuration
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

#IAM
variable "is_eks_role_enabled" {
  type = bool
}
variable "is_eks_nodegroup_role_enabled" {
  type = bool
}

# EKS
variable "is-eks-cluster-enabled" {}
variable "cluster-version" {}
variable "endpoint-private-access" {}
variable "endpoint-public-access" {}
variable "addons" {
  type = list(object({
    name    = string
    version = string
  }))
}
variable "resource_prefix" {
  type = string
  description = "Short prefix used for resource names (e.g., devops-openagent)"
}

variable "ebs_csi_driver_policy_name" {
  type        = string
  description = "IAM managed policy name for the EBS CSI driver role"
  default     = "AmazonEBSCSIDriverPolicy"
}

variable "ondemand_instance_types" {}
variable "spot_instance_types" {}
variable "desired_capacity_on_demand" {}
variable "min_capacity_on_demand" {}
variable "max_capacity_on_demand" {}
variable "desired_capacity_spot" {}
variable "min_capacity_spot" {}
variable "max_capacity_spot" {}