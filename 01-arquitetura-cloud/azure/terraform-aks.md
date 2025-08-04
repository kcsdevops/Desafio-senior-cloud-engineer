# Terraform Modules para Azure - EKS/AKS

## Azure Kubernetes Service (AKS) Module

### main.tf
```hcl
# Azure AKS Cluster Module
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

# Resource Group
resource "azurerm_resource_group" "aks" {
  name     = "rg-${var.cluster_name}-${var.environment}"
  location = var.location
  
  tags = merge(var.tags, {
    Environment = var.environment
    Component   = "AKS"
  })
}

# Virtual Network
resource "azurerm_virtual_network" "aks" {
  name                = "vnet-${var.cluster_name}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  address_space       = [var.vnet_cidr]
  
  tags = var.tags
}

# Subnet for AKS
resource "azurerm_subnet" "aks" {
  name                 = "subnet-aks"
  resource_group_name  = azurerm_resource_group.aks.name
  virtual_network_name = azurerm_virtual_network.aks.name
  address_prefixes     = [var.aks_subnet_cidr]
}

# Network Security Group
resource "azurerm_network_security_group" "aks" {
  name                = "nsg-${var.cluster_name}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name

  security_rule {
    name                       = "AllowHTTPS"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "AllowHTTP"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = var.tags
}

# Associate NSG with subnet
resource "azurerm_subnet_network_security_group_association" "aks" {
  subnet_id                 = azurerm_subnet.aks.id
  network_security_group_id = azurerm_network_security_group.aks.id
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "aks" {
  name                = "log-${var.cluster_name}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days

  tags = var.tags
}

# Azure Container Registry
resource "azurerm_container_registry" "aks" {
  count               = var.enable_acr ? 1 : 0
  name                = "acr${replace(var.cluster_name, "-", "")}"
  resource_group_name = azurerm_resource_group.aks.name
  location            = azurerm_resource_group.aks.location
  sku                 = var.acr_sku
  admin_enabled       = false

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# User Assigned Managed Identity for AKS
resource "azurerm_user_assigned_identity" "aks" {
  name                = "id-${var.cluster_name}"
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name

  tags = var.tags
}

# Role assignment for AKS to ACR
resource "azurerm_role_assignment" "aks_acr" {
  count                = var.enable_acr ? 1 : 0
  scope                = azurerm_container_registry.aks[0].id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.cluster_name
  location            = azurerm_resource_group.aks.location
  resource_group_name = azurerm_resource_group.aks.name
  dns_prefix          = "${var.cluster_name}-dns"
  kubernetes_version  = var.kubernetes_version

  default_node_pool {
    name                = "default"
    node_count          = var.node_count
    vm_size             = var.node_vm_size
    vnet_subnet_id      = azurerm_subnet.aks.id
    enable_auto_scaling = var.enable_auto_scaling
    min_count          = var.enable_auto_scaling ? var.min_nodes : null
    max_count          = var.enable_auto_scaling ? var.max_nodes : null
    os_disk_size_gb    = var.os_disk_size_gb
    
    upgrade_settings {
      max_surge = "10%"
    }

    tags = var.tags
  }

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks.id]
  }

  network_profile {
    network_plugin    = "azure"
    load_balancer_sku = "standard"
    outbound_type     = "loadBalancer"
  }

  # Enable Azure Policy
  azure_policy_enabled = var.enable_azure_policy

  # Enable RBAC
  role_based_access_control_enabled = true

  azure_active_directory_role_based_access_control {
    managed                = true
    admin_group_object_ids = var.admin_group_object_ids
    azure_rbac_enabled     = true
  }

  # Enable monitoring
  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.aks.id
  }

  # Enable Key Vault integration
  key_vault_secrets_provider {
    secret_rotation_enabled = true
  }

  # Enable Workload Identity
  workload_identity_enabled = true
  oidc_issuer_enabled      = true

  tags = var.tags

  depends_on = [
    azurerm_subnet_network_security_group_association.aks
  ]
}

# Additional Node Pool (optional)
resource "azurerm_kubernetes_cluster_node_pool" "additional" {
  count                 = var.enable_additional_node_pool ? 1 : 0
  name                  = var.additional_node_pool_name
  kubernetes_cluster_id = azurerm_kubernetes_cluster.aks.id
  vm_size              = var.additional_node_vm_size
  node_count           = var.additional_node_count
  vnet_subnet_id       = azurerm_subnet.aks.id
  enable_auto_scaling  = true
  min_count           = var.additional_min_nodes
  max_count           = var.additional_max_nodes
  
  node_taints = var.additional_node_taints
  node_labels = var.additional_node_labels

  tags = var.tags
}

# Diagnostic Settings
resource "azurerm_monitor_diagnostic_setting" "aks" {
  name                       = "diag-${var.cluster_name}"
  target_resource_id         = azurerm_kubernetes_cluster.aks.id
  log_analytics_workspace_id = azurerm_log_analytics_workspace.aks.id

  enabled_log {
    category = "kube-apiserver"
  }

  enabled_log {
    category = "kube-controller-manager"
  }

  enabled_log {
    category = "kube-scheduler"
  }

  enabled_log {
    category = "kube-audit"
  }

  enabled_log {
    category = "cluster-autoscaler"
  }

  metric {
    category = "AllMetrics"
    enabled  = true
  }
}
```

### variables.tf
```hcl
variable "cluster_name" {
  description = "Name of the AKS cluster"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.27.3"
}

variable "node_count" {
  description = "Initial number of nodes"
  type        = number
  default     = 3
}

variable "node_vm_size" {
  description = "VM size for nodes"
  type        = string
  default     = "Standard_D2s_v3"
}

variable "enable_auto_scaling" {
  description = "Enable cluster auto-scaling"
  type        = bool
  default     = true
}

variable "min_nodes" {
  description = "Minimum number of nodes"
  type        = number
  default     = 1
}

variable "max_nodes" {
  description = "Maximum number of nodes"
  type        = number
  default     = 10
}

variable "os_disk_size_gb" {
  description = "OS disk size in GB"
  type        = number
  default     = 30
}

variable "vnet_cidr" {
  description = "CIDR block for VNet"
  type        = string
  default     = "10.1.0.0/16"
}

variable "aks_subnet_cidr" {
  description = "CIDR block for AKS subnet"
  type        = string
  default     = "10.1.1.0/24"
}

variable "enable_acr" {
  description = "Enable Azure Container Registry"
  type        = bool
  default     = true
}

variable "acr_sku" {
  description = "ACR SKU"
  type        = string
  default     = "Basic"
}

variable "log_retention_days" {
  description = "Log retention in days"
  type        = number
  default     = 30
}

variable "enable_azure_policy" {
  description = "Enable Azure Policy"
  type        = bool
  default     = true
}

variable "admin_group_object_ids" {
  description = "Azure AD admin group object IDs"
  type        = list(string)
  default     = []
}

variable "enable_additional_node_pool" {
  description = "Enable additional node pool"
  type        = bool
  default     = false
}

variable "additional_node_pool_name" {
  description = "Name of additional node pool"
  type        = string
  default     = "compute"
}

variable "additional_node_vm_size" {
  description = "VM size for additional node pool"
  type        = string
  default     = "Standard_D4s_v3"
}

variable "additional_node_count" {
  description = "Node count for additional node pool"
  type        = number
  default     = 2
}

variable "additional_min_nodes" {
  description = "Min nodes for additional node pool"
  type        = number
  default     = 0
}

variable "additional_max_nodes" {
  description = "Max nodes for additional node pool"
  type        = number
  default     = 5
}

variable "additional_node_taints" {
  description = "Taints for additional node pool"
  type        = list(string)
  default     = []
}

variable "additional_node_labels" {
  description = "Labels for additional node pool"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default = {
    ManagedBy = "Terraform"
    Project   = "AKS-Cluster"
  }
}
```

### outputs.tf
```hcl
output "cluster_id" {
  description = "AKS cluster ID"
  value       = azurerm_kubernetes_cluster.aks.id
}

output "cluster_name" {
  description = "AKS cluster name"
  value       = azurerm_kubernetes_cluster.aks.name
}

output "resource_group_name" {
  description = "Resource group name"
  value       = azurerm_resource_group.aks.name
}

output "location" {
  description = "AKS cluster location"
  value       = azurerm_kubernetes_cluster.aks.location
}

output "kube_config" {
  description = "Kubernetes configuration"
  value       = azurerm_kubernetes_cluster.aks.kube_config_raw
  sensitive   = true
}

output "cluster_fqdn" {
  description = "AKS cluster FQDN"
  value       = azurerm_kubernetes_cluster.aks.fqdn
}

output "node_resource_group" {
  description = "Node resource group name"
  value       = azurerm_kubernetes_cluster.aks.node_resource_group
}

output "kubelet_identity" {
  description = "Kubelet managed identity"
  value = {
    client_id   = azurerm_kubernetes_cluster.aks.kubelet_identity[0].client_id
    object_id   = azurerm_kubernetes_cluster.aks.kubelet_identity[0].user_assigned_identity_id
    principal_id = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
  }
}

output "oidc_issuer_url" {
  description = "OIDC issuer URL"
  value       = azurerm_kubernetes_cluster.aks.oidc_issuer_url
}

output "log_analytics_workspace_id" {
  description = "Log Analytics workspace ID"
  value       = azurerm_log_analytics_workspace.aks.id
}

output "acr_id" {
  description = "Azure Container Registry ID"
  value       = var.enable_acr ? azurerm_container_registry.aks[0].id : null
}

output "acr_login_server" {
  description = "Azure Container Registry login server"
  value       = var.enable_acr ? azurerm_container_registry.aks[0].login_server : null
}

output "vnet_id" {
  description = "Virtual Network ID"
  value       = azurerm_virtual_network.aks.id
}

output "subnet_id" {
  description = "AKS subnet ID"
  value       = azurerm_subnet.aks.id
}

output "user_assigned_identity_id" {
  description = "User assigned identity ID"
  value       = azurerm_user_assigned_identity.aks.id
}

output "user_assigned_identity_client_id" {
  description = "User assigned identity client ID"
  value       = azurerm_user_assigned_identity.aks.client_id
}
```

## Usage Example

```hcl
# main.tf
module "aks_cluster" {
  source = "./modules/aks-cluster"

  cluster_name        = "aks-production"
  environment         = "prod"
  location           = "East US"
  kubernetes_version = "1.27.3"
  
  # Node configuration
  node_count          = 3
  node_vm_size       = "Standard_D2s_v3"
  enable_auto_scaling = true
  min_nodes          = 2
  max_nodes          = 10
  
  # Network configuration
  vnet_cidr       = "10.1.0.0/16"
  aks_subnet_cidr = "10.1.1.0/24"
  
  # Enable features
  enable_acr          = true
  enable_azure_policy = true
  
  # Azure AD integration
  admin_group_object_ids = [
    "00000000-0000-0000-0000-000000000000"
  ]
  
  # Additional node pool
  enable_additional_node_pool = true
  additional_node_pool_name   = "compute"
  additional_node_vm_size     = "Standard_D4s_v3"
  additional_node_count       = 2
  additional_min_nodes        = 0
  additional_max_nodes        = 5
  
  tags = {
    Environment = "Production"
    Project     = "EventDriven"
    Owner       = "Platform Team"
    CostCenter  = "Engineering"
  }
}
```

## Key Features

- **Security**: Azure AD integration, RBAC, Network Security Groups
- **Monitoring**: Log Analytics, Application Insights integration  
- **Scalability**: Auto-scaling, multiple node pools
- **Networking**: VNet integration, private networking
- **Container Registry**: Integrated ACR with proper permissions
- **Identity**: Managed Identity, Workload Identity
- **Compliance**: Azure Policy integration
- **High Availability**: Multi-zone deployment ready

Este módulo Terraform fornece uma base sólida para deploy de clusters AKS em produção com todas as best practices de segurança e observabilidade!
