# Variables for EKS Cluster Module

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
}

variable "cluster_version" {
  description = "Kubernetes version to use for the EKS cluster"
  type        = string
  default     = "1.27"
}

variable "vpc_id" {
  description = "ID of the VPC where to create the cluster"
  type        = string
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "subnet_ids" {
  description = "List of subnet IDs where the cluster and nodes will be deployed"
  type        = list(string)
}

variable "cluster_endpoint_private_access" {
  description = "Indicates whether or not the Amazon EKS private API server endpoint is enabled"
  type        = bool
  default     = true
}

variable "cluster_endpoint_public_access" {
  description = "Indicates whether or not the Amazon EKS public API server endpoint is enabled"
  type        = bool
  default     = true
}

variable "cluster_endpoint_public_access_cidrs" {
  description = "List of CIDR blocks which can access the Amazon EKS public API server endpoint"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "cluster_enabled_log_types" {
  description = "A list of the desired control plane logging to enable"
  type        = list(string)
  default     = ["api", "audit", "authenticator", "controllerManager", "scheduler"]
}

variable "cloudwatch_log_retention_in_days" {
  description = "Number of days to retain log events in CloudWatch logs"
  type        = number
  default     = 14
}

variable "node_groups" {
  description = "Map of EKS managed node group definitions to create"
  type = map(object({
    ami_id                     = optional(string)
    instance_types            = list(string)
    capacity_type             = optional(string, "ON_DEMAND")
    min_size                  = number
    max_size                  = number
    desired_size              = number
    max_unavailable_percentage = optional(number, 25)
    disk_size                 = optional(number, 50)
    labels                    = optional(map(string), {})
    taints = optional(list(object({
      key    = string
      value  = string
      effect = string
    })), [])
  }))
  default = {}
}

variable "cluster_addons" {
  description = "Map of cluster addon configurations to enable for the cluster"
  type = map(object({
    version                  = optional(string)
    resolve_conflicts        = optional(string, "OVERWRITE")
    service_account_role_arn = optional(string)
  }))
  default = {
    coredns = {
      version = "v1.10.1-eksbuild.2"
    }
    kube-proxy = {
      version = "v1.27.3-eksbuild.1"
    }
    vpc-cni = {
      version = "v1.13.4-eksbuild.1"
    }
    aws-ebs-csi-driver = {
      version = "v1.20.0-eksbuild.1"
    }
  }
}

variable "enable_irsa" {
  description = "Determines whether to create an IAM OpenID Connect Provider for EKS to enable IRSA"
  type        = bool
  default     = true
}

variable "service_accounts" {
  description = "Map of service account configurations for IRSA"
  type = map(object({
    namespace    = string
    policies     = optional(list(string), [])
    policy_arns  = optional(list(string), [])
  }))
  default = {}
}

variable "tags" {
  description = "A map of tags to add to all resources"
  type        = map(string)
  default     = {}
}
