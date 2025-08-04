# Terraform values configuration
# Copy this file to terraform.tfvars and customize as needed

# Basic cluster configuration
resource_group_name = "rg-gitops-demo"
location           = "East US"
cluster_name       = "aks-gitops-cluster"
kubernetes_version = "1.28.5"

# Node configuration
node_count    = 2
node_vm_size  = "Standard_B2s"

# ArgoCD configuration
argocd_admin_password = "GitOps@2024!"
domain_name          = "gitops-demo.local"

# Git repository for ArgoCD
git_repository_url = "https://github.com/kcsdevops/Desafio-senior-cloud-engineer.git"

# Azure AD OIDC (optional - leave empty if not using)
azure_ad_client_id = ""

# Resource tags
tags = {
  Environment = "demo"
  Project     = "gitops"
  Purpose     = "senior-cloud-engineer-test"
  CreatedBy   = "terraform"
  Owner       = "cloud-engineer"
  CostCenter  = "engineering"
}
