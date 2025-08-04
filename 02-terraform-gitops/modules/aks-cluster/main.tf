# AKS Cluster Module for Azure

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
  }
}

# Configure providers
provider "kubernetes" {
  host                   = azurerm_kubernetes_cluster.main.kube_config.0.host
  client_certificate     = base64decode(azurerm_kubernetes_cluster.main.kube_config.0.client_certificate)
  client_key            = base64decode(azurerm_kubernetes_cluster.main.kube_config.0.client_key)
  cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.main.kube_config.0.cluster_ca_certificate)
}

provider "helm" {
  kubernetes {
    host                   = azurerm_kubernetes_cluster.main.kube_config.0.host
    client_certificate     = base64decode(azurerm_kubernetes_cluster.main.kube_config.0.client_certificate)
    client_key            = base64decode(azurerm_kubernetes_cluster.main.kube_config.0.client_key)
    cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.main.kube_config.0.cluster_ca_certificate)
  }
}

# Data sources
data "azurerm_client_config" "current" {}

data "azuread_client_config" "current" {}

# Log Analytics Workspace for monitoring
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.cluster_name}-logs"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days

  tags = var.tags
}

# User Assigned Managed Identity for AKS
resource "azurerm_user_assigned_identity" "aks" {
  name                = "${var.cluster_name}-identity"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = var.tags
}

# Role assignments for AKS managed identity
resource "azurerm_role_assignment" "network_contributor" {
  scope                = var.vnet_subnet_id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

resource "azurerm_role_assignment" "acr_pull" {
  count                = var.acr_id != null ? 1 : 0
  scope                = var.acr_id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "main" {
  name                = var.cluster_name
  location            = var.location
  resource_group_name = var.resource_group_name
  dns_prefix          = "${var.cluster_name}-dns"
  kubernetes_version  = var.kubernetes_version

  # System node pool
  default_node_pool {
    name                = var.default_node_pool.name
    node_count          = var.default_node_pool.node_count
    vm_size            = var.default_node_pool.vm_size
    vnet_subnet_id     = var.vnet_subnet_id
    enable_auto_scaling = var.default_node_pool.enable_auto_scaling
    min_count          = var.default_node_pool.enable_auto_scaling ? var.default_node_pool.min_count : null
    max_count          = var.default_node_pool.enable_auto_scaling ? var.default_node_pool.max_count : null
    
    # Security configurations
    enable_host_encryption = true
    enable_node_public_ip  = false
    
    node_labels = merge(
      var.default_node_pool.node_labels,
      {
        "nodepool-type" = "system"
        "environment"   = var.environment
      }
    )
    
    node_taints = var.default_node_pool.node_taints
    
    zones = var.availability_zones
    
    # Upgrade settings
    upgrade_settings {
      max_surge = "33%"
    }
  }

  # Identity configuration
  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.aks.id]
  }

  # Network configuration
  network_profile {
    network_plugin    = var.network_plugin
    network_policy    = var.network_policy
    dns_service_ip    = var.dns_service_ip
    service_cidr      = var.service_cidr
    load_balancer_sku = "standard"
  }

  # RBAC and Azure AD integration
  dynamic "azure_active_directory_role_based_access_control" {
    for_each = var.rbac_enabled ? [1] : []
    content {
      managed                = true
      admin_group_object_ids = var.admin_group_object_ids
      azure_rbac_enabled     = var.azure_rbac_enabled
    }
  }

  # Monitoring
  oms_agent {
    log_analytics_workspace_id      = azurerm_log_analytics_workspace.main.id
    msi_auth_for_monitoring_enabled = true
  }

  # Key Vault integration
  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }

  # Workload Identity
  workload_identity_enabled = var.workload_identity_enabled
  oidc_issuer_enabled      = var.oidc_issuer_enabled

  # Auto upgrade
  automatic_channel_upgrade = var.automatic_channel_upgrade

  # Maintenance window
  dynamic "maintenance_window" {
    for_each = var.maintenance_window != null ? [var.maintenance_window] : []
    content {
      allowed {
        day   = maintenance_window.value.day
        hours = maintenance_window.value.hours
      }
    }
  }

  # API server configuration
  api_server_access_profile {
    vnet_integration_enabled = var.private_cluster_enabled
    subnet_id               = var.private_cluster_enabled ? var.api_server_subnet_id : null
    authorized_ip_ranges    = var.authorized_ip_ranges
  }

  tags = var.tags

  depends_on = [
    azurerm_role_assignment.network_contributor,
    azurerm_role_assignment.acr_pull
  ]
}

# Additional node pools
resource "azurerm_kubernetes_cluster_node_pool" "additional" {
  for_each = var.additional_node_pools

  name                  = each.key
  kubernetes_cluster_id = azurerm_kubernetes_cluster.main.id
  vm_size              = each.value.vm_size
  node_count           = each.value.node_count
  vnet_subnet_id       = var.vnet_subnet_id

  # Auto scaling
  enable_auto_scaling = each.value.enable_auto_scaling
  min_count          = each.value.enable_auto_scaling ? each.value.min_count : null
  max_count          = each.value.enable_auto_scaling ? each.value.max_count : null

  # Security
  enable_host_encryption = true
  enable_node_public_ip  = false

  # Node configuration
  node_labels = each.value.node_labels
  node_taints = each.value.node_taints
  zones       = var.availability_zones

  # Upgrade settings
  upgrade_settings {
    max_surge = "33%"
  }

  tags = var.tags
}

# Workload Identity resources for service accounts
resource "azurerm_user_assigned_identity" "workload_identity" {
  for_each = var.workload_identities

  name                = "${var.cluster_name}-${each.key}-identity"
  location            = var.location
  resource_group_name = var.resource_group_name

  tags = var.tags
}

resource "azurerm_federated_identity_credential" "workload_identity" {
  for_each = var.workload_identities

  name                = "${var.cluster_name}-${each.key}-federated-credential"
  resource_group_name = var.resource_group_name
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.main.oidc_issuer_url
  parent_id           = azurerm_user_assigned_identity.workload_identity[each.key].id
  subject             = "system:serviceaccount:${each.value.namespace}:${each.value.service_account_name}"
}

# Role assignments for workload identities
resource "azurerm_role_assignment" "workload_identity" {
  for_each = {
    for key, config in var.workload_identities : key => config
    if config.role_assignments != null
  }

  scope                = each.value.role_assignments.scope
  role_definition_name = each.value.role_assignments.role_definition_name
  principal_id         = azurerm_user_assigned_identity.workload_identity[each.key].principal_id
}

# Kubernetes service accounts with workload identity
resource "kubernetes_service_account" "workload_identity" {
  for_each = var.workload_identities

  metadata {
    name      = each.value.service_account_name
    namespace = each.value.namespace
    annotations = {
      "azure.workload.identity/client-id" = azurerm_user_assigned_identity.workload_identity[each.key].client_id
    }
    labels = {
      "azure.workload.identity/use" = "true"
    }
  }

  depends_on = [azurerm_kubernetes_cluster.main]
}

# Install essential addons using Helm
resource "helm_release" "ingress_nginx" {
  count = var.install_ingress_nginx ? 1 : 0

  name       = "ingress-nginx"
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  namespace  = "ingress-nginx"
  version    = var.ingress_nginx_version

  create_namespace = true

  values = [yamlencode({
    controller = {
      replicaCount = 2
      service = {
        loadBalancerSourceRanges = var.ingress_allowed_cidrs
      }
      resources = {
        requests = {
          cpu    = "100m"
          memory = "90Mi"
        }
        limits = {
          cpu    = "200m"
          memory = "256Mi"
        }
      }
      metrics = {
        enabled = true
      }
    }
  })]

  depends_on = [azurerm_kubernetes_cluster.main]
}

resource "helm_release" "cert_manager" {
  count = var.install_cert_manager ? 1 : 0

  name       = "cert-manager"
  repository = "https://charts.jetstack.io"
  chart      = "cert-manager"
  namespace  = "cert-manager"
  version    = var.cert_manager_version

  create_namespace = true

  set {
    name  = "installCRDs"
    value = "true"
  }

  set {
    name  = "global.leaderElection.namespace"
    value = "cert-manager"
  }

  depends_on = [azurerm_kubernetes_cluster.main]
}
