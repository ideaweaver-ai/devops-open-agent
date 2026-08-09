locals {
  prefix = "devops-openagent"
  env    = var.env
}

module "eks" {
  source = "../modules"
  env    = var.env
  # Use a fixed prefix to keep resource names predictable: devops-openagent-cluster
  cluster-name                   = "${local.prefix}-cluster"
  cidr-block                     = var.vpc-cidr-block
  vpc-name                       = "${local.prefix}-vpc"
  base_infra_s3_bucket_name      = var.base_infra_s3_bucket_name
  base_infra_dynamodb_table_name = var.base_infra_dynamodb_table_name
  igw-name                       = "${local.prefix}-igw"
  pub-subnet-count               = var.pub-subnet-count
  pub-cidr-block                 = var.pub-cidr-block
  pub-availability-zone          = var.pub-availability-zone
  pub-sub-name                   = "${local.prefix}-pub-sub"
  pri-subnet-count               = var.pri-subnet-count
  pri-cidr-block                 = var.pri-cidr-block
  pri-availability-zone          = var.pri-availability-zone
  pri-sub-name                   = "${local.prefix}-priv-sub"
  public-rt-name                 = "${local.prefix}-pub-rt"
  private-rt-name                = "${local.prefix}-priv-rt"
  eip-name                       = "${local.prefix}-eip"
  ngw-name                       = "${local.prefix}-ngw"
  eks-sg                         = "${local.prefix}-sg"
  resource_prefix                = local.prefix

  is_eks_role_enabled           = true
  is_eks_nodegroup_role_enabled = true
  ondemand_instance_types       = var.ondemand_instance_types
  spot_instance_types           = var.spot_instance_types
  desired_capacity_on_demand    = var.desired_capacity_on_demand
  min_capacity_on_demand        = var.min_capacity_on_demand
  max_capacity_on_demand        = var.max_capacity_on_demand
  desired_capacity_spot         = var.desired_capacity_spot
  min_capacity_spot             = var.min_capacity_spot
  max_capacity_spot             = var.max_capacity_spot
  is-eks-cluster-enabled        = var.is-eks-cluster-enabled
  cluster-version               = var.cluster-version
  endpoint-private-access       = var.endpoint-private-access
  endpoint-public-access        = var.endpoint-public-access

  create_bastion              = var.create_bastion
  bastion_instance_type       = var.bastion_instance_type
  bastion_public_subnet_index = var.bastion_public_subnet_index
  bastion_allowed_cidr_blocks = var.bastion_allowed_cidr_blocks

  addons = var.addons
}