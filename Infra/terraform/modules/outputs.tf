output "bastion_instance_id" {
  value = length(aws_instance.bastion) > 0 ? aws_instance.bastion[0].id : ""
}

output "bastion_public_ip" {
  value = length(aws_instance.bastion) > 0 ? aws_instance.bastion[0].public_ip : ""
}

output "bastion_key_name" {
  value = length(aws_key_pair.bastion_key) > 0 ? aws_key_pair.bastion_key[0].key_name : ""
}

// WARNING: this will store the private key in state. Handle securely.
output "bastion_private_key_pem" {
  value     = length(tls_private_key.bastion) > 0 ? tls_private_key.bastion[0].private_key_pem : ""
  sensitive = true
}

output "vpc_id" {
  description = "ID of the created VPC"
  value       = aws_vpc.vpc.id
}

output "vpc_name" {
  description = "Name tag of the created VPC"
  value       = aws_vpc.vpc.tags["Name"]
}

output "vpc_cidr_block" {
  description = "CIDR block for the created VPC"
  value       = aws_vpc.vpc.cidr_block
}

# EKS cluster outputs
output "eks_cluster_name" {
  description = "EKS cluster name"
  value       = length(aws_eks_cluster.eks) > 0 ? aws_eks_cluster.eks[0].name : ""
}

output "eks_cluster_endpoint" {
  description = "EKS cluster API endpoint"
  value       = length(aws_eks_cluster.eks) > 0 ? aws_eks_cluster.eks[0].endpoint : ""
}

output "eks_cluster_ca_data" {
  description = "EKS cluster certificate authority data (base64)"
  value       = length(aws_eks_cluster.eks) > 0 ? aws_eks_cluster.eks[0].certificate_authority[0].data : ""
  sensitive   = true
}

output "eks_cluster_arn" {
  description = "EKS cluster ARN"
  value       = length(aws_eks_cluster.eks) > 0 ? aws_eks_cluster.eks[0].arn : ""
}

output "eks_console_url" {
  description = "AWS Console URL for the EKS cluster"
  value       = length(aws_eks_cluster.eks) > 0 ? "https://console.aws.amazon.com/eks/home#/clusters/${aws_eks_cluster.eks[0].name}/overview" : ""
}

# kubeconfig that can be written to ~/.kube/config (uses aws eks get-token to authenticate)
output "kubeconfig" {
  description = "Kubeconfig YAML for the created EKS cluster (use with care)."
  value = length(aws_eks_cluster.eks) > 0 ? (<<-KUBECONF
apiVersion: v1
clusters:
- cluster:
    server: ${aws_eks_cluster.eks[0].endpoint}
    certificate-authority-data: ${aws_eks_cluster.eks[0].certificate_authority[0].data}
  name: ${aws_eks_cluster.eks[0].name}
contexts:
- context:
    cluster: ${aws_eks_cluster.eks[0].name}
    user: aws
  name: ${aws_eks_cluster.eks[0].name}
current-context: ${aws_eks_cluster.eks[0].name}
users:
- name: aws
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      command: aws
      args:
        - "eks"
        - "get-token"
        - "--cluster-name"
        - "${aws_eks_cluster.eks[0].name}"
KUBECONF
) : ""
  sensitive = true
}
