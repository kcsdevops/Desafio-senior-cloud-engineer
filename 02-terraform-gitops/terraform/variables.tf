# Variables for AKS GitOps deployment

variable "resource_group_name" {
  description = "Name of the Azure Resource Group"
  type        = string
  default     = "rg-gitops-demo"
}

variable "location" {
  description = "Azure region for resources"
  type        = string
  default     = "East US"
}

variable "cluster_name" {
  description = "Name of the AKS cluster"
  type        = string
  default     = "aks-gitops-cluster"
}

variable "kubernetes_version" {
  description = "Kubernetes version for AKS"
  type        = string
  default     = "1.28.5"
}

variable "node_count" {
  description = "Number of nodes in the default node pool"
  type        = number
  default     = 2
}

variable "node_vm_size" {
  description = "VM size for AKS nodes"
  type        = string
  default     = "Standard_B2s"
}

variable "argocd_admin_password" {
  description = "Admin password for ArgoCD"
  type        = string
  default     = "GitOps@2024!"
  sensitive   = true
}

variable "domain_name" {
  description = "Domain name for ingress"
  type        = string
  default     = "gitops-demo.local"
}

variable "azure_ad_client_id" {
  description = "Azure AD application client ID for OIDC"
  type        = string
  default     = ""
}

variable "git_repository_url" {
  description = "Git repository URL for ArgoCD applications"
  type        = string
  default     = "https://github.com/kcsdevops/Desafio-senior-cloud-engineer.git"
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Environment = "demo"
    Project     = "gitops"
    Purpose     = "senior-cloud-engineer-test"
    CreatedBy   = "terraform"  
  }
}
