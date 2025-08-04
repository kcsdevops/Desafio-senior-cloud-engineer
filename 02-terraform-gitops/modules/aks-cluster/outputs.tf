# AKS Cluster Module Outputs

output "cluster_id" {
  description = "ID of the AKS cluster"
  value       = azurerm_kubernetes_cluster.main.id
}

output "cluster_name" {
  description = "Name of the AKS cluster"
  value       = azurerm_kubernetes_cluster.main.name
}

output "cluster_fqdn" {
  description = "FQDN of the AKS cluster API server"
  value       = azurerm_kubernetes_cluster.main.fqdn
}

output "cluster_private_fqdn" {
  description = "Private FQDN of the AKS cluster API server"
  value       = azurerm_kubernetes_cluster.main.private_fqdn
}

output "kube_config" {
  description = "Kubernetes configuration"
  value       = azurerm_kubernetes_cluster.main.kube_config
  sensitive   = true
}

output "kube_config_raw" {
  description = "Raw Kubernetes configuration"
  value       = azurerm_kubernetes_cluster.main.kube_config_raw
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "Base64 encoded CA certificate of the AKS cluster"
  value       = azurerm_kubernetes_cluster.main.kube_config.0.cluster_ca_certificate
  sensitive   = true
}

output "host" {
  description = "Host of the AKS cluster API server"
  value       = azurerm_kubernetes_cluster.main.kube_config.0.host
  sensitive   = true
}

output "client_certificate" {
  description = "Base64 encoded client certificate"
  value       = azurerm_kubernetes_cluster.main.kube_config.0.client_certificate
  sensitive   = true
}

output "client_key" {
  description = "Base64 encoded client key"
  value       = azurerm_kubernetes_cluster.main.kube_config.0.client_key
  sensitive   = true
}

output "oidc_issuer_url" {
  description = "OIDC issuer URL for workload identity"
  value       = azurerm_kubernetes_cluster.main.oidc_issuer_url
}

output "kubelet_identity" {
  description = "Kubelet identity configuration"
  value = {
    client_id                 = azurerm_kubernetes_cluster.main.kubelet_identity[0].client_id
    object_id                = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
    user_assigned_identity_id = azurerm_kubernetes_cluster.main.kubelet_identity[0].user_assigned_identity_id
  }
}

output "cluster_identity" {
  description = "Cluster managed identity"
  value = {
    principal_id = azurerm_kubernetes_cluster.main.identity[0].principal_id
    tenant_id    = azurerm_kubernetes_cluster.main.identity[0].tenant_id
    type         = azurerm_kubernetes_cluster.main.identity[0].type
    identity_ids = azurerm_kubernetes_cluster.main.identity[0].identity_ids
  }
}

output "user_assigned_identity" {
  description = "User assigned identity for the cluster"
  value = {
    id           = azurerm_user_assigned_identity.aks.id
    client_id    = azurerm_user_assigned_identity.aks.client_id
    principal_id = azurerm_user_assigned_identity.aks.principal_id
  }
}

output "workload_identities" {
  description = "Workload identities created for service accounts"
  value = {
    for key, identity in azurerm_user_assigned_identity.workload_identity :
    key => {
      id           = identity.id
      client_id    = identity.client_id
      principal_id = identity.principal_id
    }
  }
}

output "log_analytics_workspace" {
  description = "Log Analytics workspace information"
  value = {
    id                  = azurerm_log_analytics_workspace.main.id
    workspace_id        = azurerm_log_analytics_workspace.main.workspace_id
    primary_shared_key  = azurerm_log_analytics_workspace.main.primary_shared_key
    secondary_shared_key = azurerm_log_analytics_workspace.main.secondary_shared_key
  }
  sensitive = true
}

output "node_resource_group" {
  description = "Name of the resource group containing AKS nodes"
  value       = azurerm_kubernetes_cluster.main.node_resource_group
}

output "effective_outbound_ips" {
  description = "Effective outbound IP addresses"
  value       = azurerm_kubernetes_cluster.main.network_profile[0].load_balancer_profile[0].effective_outbound_ips
}

output "cluster_portal_fqdn" {
  description = "Portal FQDN for the AKS cluster"
  value       = azurerm_kubernetes_cluster.main.portal_fqdn
}

output "ingress_nginx_ip" {
  description = "External IP of the NGINX Ingress Controller (if installed)"
  value = var.install_ingress_nginx ? (
    try(
      data.kubernetes_service.ingress_nginx[0].status[0].load_balancer[0].ingress[0].ip,
      null
    )
  ) : null
}

# Data source for ingress service IP (conditional)
data "kubernetes_service" "ingress_nginx" {
  count = var.install_ingress_nginx ? 1 : 0
  
  metadata {
    name      = "ingress-nginx-controller"
    namespace = "ingress-nginx"
  }
  
  depends_on = [helm_release.ingress_nginx]
}

# Output for connection command
output "kubectl_config_command" {
  description = "Command to configure kubectl"
  value       = "az aks get-credentials --resource-group ${var.resource_group_name} --name ${var.cluster_name}"
}

output "cluster_info" {
  description = "Comprehensive cluster information"
  value = {
    name                = azurerm_kubernetes_cluster.main.name
    kubernetes_version  = azurerm_kubernetes_cluster.main.kubernetes_version
    location           = azurerm_kubernetes_cluster.main.location
    resource_group     = azurerm_kubernetes_cluster.main.resource_group_name
    node_resource_group = azurerm_kubernetes_cluster.main.node_resource_group
    fqdn               = azurerm_kubernetes_cluster.main.fqdn
    private_fqdn       = azurerm_kubernetes_cluster.main.private_fqdn
    portal_fqdn        = azurerm_kubernetes_cluster.main.portal_fqdn
    oidc_issuer_url    = azurerm_kubernetes_cluster.main.oidc_issuer_url
  }
}
