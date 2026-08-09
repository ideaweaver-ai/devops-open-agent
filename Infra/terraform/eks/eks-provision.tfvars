env                   = "dev"
aws-region            = "us-east-1"
vpc-cidr-block        = "10.16.0.0/16"
vpc-name              = "devops-vpc"
igw-name              = "devops-igw"
pub-subnet-count      = 3
pub-cidr-block        = ["10.16.0.0/20", "10.16.16.0/20", "10.16.32.0/20"]
pub-availability-zone = ["us-east-1a", "us-east-1b", "us-east-1c"]
pub-sub-name          = "subnet-public"
pri-subnet-count      = 3
pri-cidr-block        = ["10.16.128.0/20", "10.16.144.0/20", "10.16.160.0/20"]
pri-availability-zone = ["us-east-1a", "us-east-1b", "us-east-1c"]
pri-sub-name          = "subnet-private"
public-rt-name        = "public-route-table"
private-rt-name       = "private-route-table"
eip-name              = "elasticip-ngw"
ngw-name              = "devops-ngw"
eks-sg                = "devops-openagent-sg"

# EKS
is-eks-cluster-enabled     = true
cluster-version            = "1.36"
cluster-name               = "devops-openagent-cluster"
endpoint-private-access    = true
endpoint-public-access     = false
ondemand_instance_types    = ["t3a.medium"]
spot_instance_types        = ["c5a.large", "c5a.xlarge", "m5a.large", "m5a.xlarge", "c5.large", "m5.large", "t3a.large", "t3a.xlarge", "t3a.medium"]
desired_capacity_on_demand = "1"
min_capacity_on_demand     = "1"
max_capacity_on_demand     = "5"
desired_capacity_spot      = "1"
min_capacity_spot          = "1"
max_capacity_spot          = "10"
addons = [
  {
    name    = "vpc-cni"
    version = ""
  },
  {
    name    = "coredns"
    version = ""
  },
  {
    name    = "kube-proxy"
    version = ""
  },
  {
    name    = "aws-ebs-csi-driver"
    version = ""
  }
  # Add more addons as needed
]

# Bastion configuration
create_bastion        = true
bastion_instance_type = "t2.medium"
# index into public subnets (0..n-1)
bastion_public_subnet_index = 0
# Replace this with your office/home public IP or VPN exit IP
# Restrict bastion SSH access to trusted CIDR ranges only
bastion_allowed_cidr_blocks = ["203.0.113.10/32", "10.16.0.0/16"]