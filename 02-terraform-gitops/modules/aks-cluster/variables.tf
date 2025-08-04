# AKS Cluster Module Variables

variable "cluster_name" {
  description = "Name of the AKS cluster"
  type        = string
}

variable "location" {
  description = "Azure region for the AKS cluster"
  type        = string
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.27.1"
}

variable "environment" {
  description = "Environment name (e.g., production, staging, development)"
  type        = string
}

# Node Pool Configuration
variable "default_node_pool" {
  description = "Configuration for the default node pool"
  type = object({
    name                = string
    node_count          = number
    vm_size            = string
    enable_auto_scaling = bool
    min_count          = optional(number)
    max_count          = optional(number)
    node_labels        = optional(map(string), {})
    node_taints        = optional(list(string), [])
  })
  default = {
    name                = "system"
    node_count          = 2
    vm_size            = "Standard_D2s_v3"
    enable_auto_scaling = true
    min_count          = 1
    max_count          = 10
    node_labels        = {}
    node_taints        = []
  }
}

variable "additional_node_pools" {
  description = "Configuration for additional node pools"
  type = map(object({
    vm_size            = string
    node_count         = number
    enable_auto_scaling = bool
    min_count          = optional(number)
    max_count          = optional(number)
    node_labels        = optional(map(string), {})
    node_taints        = optional(list(string), [])
  }))
  default = {}
}

# Network Configuration
variable "vnet_subnet_id" {
  description = "ID of the subnet for AKS nodes"
  type        = string
}

variable "network_plugin" {
  description = "Network plugin to use for networking (azure, kubenet)"
  type        = string
  default     = "azure"
  
  validation {
    condition     = contains(["azure", "kubenet"], var.network_plugin)
    error_message = "Network plugin must be either 'azure' or 'kubenet'."
  }
}

variable "network_policy" {
  description = "Network policy to use (azure, calico)"
  type        = string
  default     = "azure"
  
  validation {
    condition     = contains(["azure", "calico"], var.network_policy)
    error_message = "Network policy must be either 'azure' or 'calico'."
  }
}

variable "dns_service_ip" {
  description = "IP address for the DNS service"
  type        = string
  default     = "10.0.0.10"
}

variable "service_cidr" {
  description = "CIDR for Kubernetes services"
  type        = string
  default     = "10.0.0.0/16"
}

# Private Cluster Configuration
variable "private_cluster_enabled" {
  description = "Enable private cluster (API server accessible only from specified networks)"
  type        = bool
  default     = false
}

variable "api_server_subnet_id" {
  description = "Subnet ID for API server when using private cluster"
  type        = string
  default     = null
}

variable "authorized_ip_ranges" {
  description = "List of authorized IP ranges for API server access"
  type        = list(string)
  default     = []
}

# RBAC Configuration
variable "rbac_enabled" {
  description = "Enable Kubernetes RBAC"
  type        = bool
  default     = true
}

variable "azure_rbac_enabled" {
  description = "Enable Azure RBAC for Kubernetes authorization"
  type        = bool
  default     = true
}

variable "admin_group_object_ids" {
  description = "List of Azure AD group object IDs that have admin access to the cluster"
  type        = list(string)
  default     = []
}

# Identity Configuration
variable "workload_identity_enabled" {
  description = "Enable workload identity"
  type        = bool
  default     = true
}

variable "oidc_issuer_enabled" {
  description = "Enable OIDC issuer"
  type        = bool
  default     = true
}

variable "workload_identities" {
  description = "Configuration for workload identities"
  type = map(object({
    namespace              = string
    service_account_name   = string
    role_assignments      = optional(object({
      scope                = string
      role_definition_name = string
    }))
  }))
  default = {}
}

# Monitoring Configuration
variable "log_retention_days" {
  description = "Number of days to retain logs in Log Analytics workspace"
  type        = number
  default     = 30
}

# ACR Configuration
variable "acr_id" {
  description = "ID of the Azure Container Registry to grant pull access"
  type        = string
  default     = null
}

# Availability Zones
variable "availability_zones" {
  description = "List of availability zones for node pools"
  type        = list(string)
  default     = ["1", "2", "3"]
}

# Maintenance Configuration
variable "automatic_channel_upgrade" {
  description = "Automatic channel upgrade option"
  type        = string
  default     = "patch"
  
  validation {
    condition     = contains(["patch", "rapid", "node-image", "stable", "none"], var.automatic_channel_upgrade)
    error_message = "Automatic channel upgrade must be one of: patch, rapid, node-image, stable, none."
  }
}

variable "maintenance_window" {
  description = "Maintenance window configuration"
  type = object({
    day   = string
    hours = list(number)
  })
  default = null
}

# Addon Configuration
variable "install_ingress_nginx" {
  description = "Install NGINX Ingress Controller"
  type        = bool
  default     = true
}

variable "ingress_nginx_version" {
  description = "Version of NGINX Ingress Controller"
  type        = string
  default     = "4.7.1"
}

variable "ingress_allowed_cidrs" {
  description = "CIDR blocks allowed to access the ingress controller"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "install_cert_manager" {
  description = "Install cert-manager for TLS certificate management"
  type        = bool
  default     = true
}

variable "cert_manager_version" {
  description = "Version of cert-manager"
  type        = string
  default     = "v1.12.2"
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
