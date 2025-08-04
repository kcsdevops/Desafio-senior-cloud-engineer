# Terraform configuration for AKS GitOps deployment

terraform {
  required_version = ">= 1.0"
  
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
    helm = {
      source  = "hashicorp/helm"
      version = "~> 2.11"
    }
    kubectl = {
      source  = "gavinbunney/kubectl"
      version = "~> 1.14"
    }
  }
}

# Configure providers
provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
}

provider "kubernetes" {
  host                   = azurerm_kubernetes_cluster.aks.kube_config.0.host
  client_certificate     = base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.client_certificate)
  client_key            = base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.client_key)
  cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.cluster_ca_certificate)
}

provider "helm" {
  kubernetes {
    host                   = azurerm_kubernetes_cluster.aks.kube_config.0.host
    client_certificate     = base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.client_certificate)
    client_key            = base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.client_key)
    cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.cluster_ca_certificate)
  }
}

provider "kubectl" {
  host                   = azurerm_kubernetes_cluster.aks.kube_config.0.host
  client_certificate     = base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.client_certificate)
  client_key            = base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.client_key)
  cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.aks.kube_config.0.cluster_ca_certificate)
  load_config_file       = false
}

# Data sources
data "azurerm_client_config" "current" {}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location

  tags = var.tags
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "${var.cluster_name}-vnet"
  address_space       = ["10.0.0.0/8"]
  location           = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = var.tags
}

# Subnet for AKS
resource "azurerm_subnet" "aks" {
  name                 = "${var.cluster_name}-aks-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = ["10.240.0.0/16"]
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.cluster_name}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.tags
}

# User Assigned Managed Identity for AKS
resource "azurerm_user_assigned_identity" "aks" {
  name                = "${var.cluster_name}-identity"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = var.tags
}

# Role assignments for AKS managed identity
resource "azurerm_role_assignment" "network_contributor" {
  scope                = azurerm_subnet.aks.id
  role_definition_name = "Network Contributor"
  principal_id         = azurerm_user_assigned_identity.aks.principal_id
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "aks" {
  name                = var.cluster_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = "${var.cluster_name}-dns"
  kubernetes_version  = var.kubernetes_version

  # Default node pool
  default_node_pool {
    name               = "system"
    node_count         = var.node_count
    vm_size           = var.node_vm_size
    vnet_subnet_id    = azurerm_subnet.aks.id
    enable_auto_scaling = true
    min_count         = 1
    max_count         = 5
    
    node_labels = {
      "nodepool-type" = "system"
      "environment"   = "gitops-demo"
    }
    
    zones = ["1", "2", "3"]
    
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
    network_plugin    = "azure"
    network_policy    = "calico"
    dns_service_ip    = "10.0.0.10"
    service_cidr      = "10.0.0.0/16"
    load_balancer_sku = "standard"
  }

  # Azure AD integration
  azure_active_directory_role_based_access_control {
    admin_group_object_ids = []
    azure_rbac_enabled     = true
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
  workload_identity_enabled = true
  oidc_issuer_enabled      = true

  tags = var.tags

  depends_on = [
    azurerm_role_assignment.network_contributor
  ]
}

# Workload Identity for ArgoCD
resource "azurerm_user_assigned_identity" "argocd" {
  name                = "${var.cluster_name}-argocd-identity"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = var.tags
}

resource "azurerm_federated_identity_credential" "argocd" {
  name                = "${var.cluster_name}-argocd-federated-credential"
  resource_group_name = azurerm_resource_group.main.name
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.aks.oidc_issuer_url
  parent_id           = azurerm_user_assigned_identity.argocd.id
  subject             = "system:serviceaccount:argocd:argocd-server"
}

# Create ArgoCD namespace
resource "kubernetes_namespace" "argocd" {
  metadata {
    name = "argocd"
    labels = {
      name = "argocd"
      "app.kubernetes.io/part-of" = "argocd"
    }
  }

  depends_on = [azurerm_kubernetes_cluster.aks]
}

# Install ArgoCD using Helm
resource "helm_release" "argocd" {
  name       = "argocd"
  repository = "https://argoproj.github.io/argo-helm"
  chart      = "argo-cd"
  namespace  = kubernetes_namespace.argocd.metadata[0].name
  version    = "5.46.7"

  values = [yamlencode({
    global = {
      image = {
        tag = "v2.8.4"
      }
    }
    
    configs = {
      secret = {
        argocdServerAdminPassword = bcrypt(var.argocd_admin_password)
      }
      
      cm = {
        "application.instanceLabelKey" = "argocd.argoproj.io/instance"
        "server.rbac.log.enforce.enable" = "true"
        "policy.default" = "role:readonly"
        "policy.csv" = <<-EOT
          p, role:admin, applications, *, */*, allow
          p, role:admin, clusters, *, *, allow
          p, role:admin, repositories, *, *, allow
          p, role:admin, certificates, *, *, allow
          p, role:admin, projects, *, *, allow
          p, role:admin, accounts, *, *, allow
          p, role:admin, gpgkeys, *, *, allow
          g, admin, role:admin
        EOT
        
        "url" = "https://argocd.${var.domain_name}"
        "oidc.config" = yamlencode({
          name = "Azure AD"
          issuer = "https://login.microsoftonline.com/${data.azurerm_client_config.current.tenant_id}/v2.0"
          clientId = var.azure_ad_client_id
          clientSecret = "$oidc.azure.clientSecret"
          requestedScopes = ["openid", "profile", "email", "groups"]
          requestedIDTokenClaims = {
            groups = {
              essential = true
            }
          }
        })
      }
    }
    
    server = {
      service = {
        type = "LoadBalancer"
        annotations = {
          "service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path" = "/healthz"
        }
      }
      
      ingress = {
        enabled = true
        ingressClassName = "nginx"
        hosts = [
          {
            host = "argocd.${var.domain_name}"
            paths = [
              {
                path = "/"
                pathType = "Prefix"
              }
            ]
          }
        ]
        tls = [
          {
            secretName = "argocd-server-tls"
            hosts = ["argocd.${var.domain_name}"]
          }
        ]
      }
      
      metrics = {
        enabled = true
        serviceMonitor = {
          enabled = true
        }
      }
    }
    
    repoServer = {
      metrics = {
        enabled = true
        serviceMonitor = {
          enabled = true
        }
      }
    }
    
    controller = {
      metrics = {
        enabled = true
        serviceMonitor = {
          enabled = true
        }
      }
    }
  })]

  depends_on = [kubernetes_namespace.argocd]
}

# Create ArgoCD service account with workload identity
resource "kubernetes_service_account" "argocd_server" {
  metadata {
    name      = "argocd-server"
    namespace = kubernetes_namespace.argocd.metadata[0].name
    annotations = {
      "azure.workload.identity/client-id" = azurerm_user_assigned_identity.argocd.client_id
    }
    labels = {
      "azure.workload.identity/use" = "true"
    }
  }

  depends_on = [helm_release.argocd]
}

# Install External Secrets Operator
resource "kubernetes_namespace" "external_secrets" {
  metadata {
    name = "external-secrets-system"
  }

  depends_on = [azurerm_kubernetes_cluster.aks]
}

resource "helm_release" "external_secrets" {
  name       = "external-secrets"
  repository = "https://charts.external-secrets.io"
  chart      = "external-secrets"
  namespace  = kubernetes_namespace.external_secrets.metadata[0].name
  version    = "0.9.9"

  set {
    name  = "installCRDs"
    value = "true"
  }

  set {
    name  = "webhook.port"
    value = "9443"
  }

  depends_on = [kubernetes_namespace.external_secrets]
}

# Install NGINX Ingress Controller
resource "kubernetes_namespace" "ingress_nginx" {
  metadata {
    name = "ingress-nginx"
  }

  depends_on = [azurerm_kubernetes_cluster.aks]
}

resource "helm_release" "nginx_ingress" {
  name       = "ingress-nginx"
  repository = "https://kubernetes.github.io/ingress-nginx"
  chart      = "ingress-nginx"
  namespace  = kubernetes_namespace.ingress_nginx.metadata[0].name
  version    = "4.8.3"

  values = [yamlencode({
    controller = {
      replicaCount = 2
      service = {
        annotations = {
          "service.beta.kubernetes.io/azure-load-balancer-health-probe-request-path" = "/healthz"
        }
      }
      metrics = {
        enabled = true
        serviceMonitor = {
          enabled = true
        }
      }
    }
  })]

  depends_on = [kubernetes_namespace.ingress_nginx]
}

# Install cert-manager
resource "kubernetes_namespace" "cert_manager" {
  metadata {
    name = "cert-manager"
  }

  depends_on = [azurerm_kubernetes_cluster.aks]
}

resource "helm_release" "cert_manager" {
  name       = "cert-manager"
  repository = "https://charts.jetstack.io"
  chart      = "cert-manager"
  namespace  = kubernetes_namespace.cert_manager.metadata[0].name
  version    = "v1.13.2"

  set {
    name  = "installCRDs"
    value = "true"
  }

  set {
    name  = "global.leaderElection.namespace"
    value = kubernetes_namespace.cert_manager.metadata[0].name
  }

  depends_on = [kubernetes_namespace.cert_manager]
}

# Create root ArgoCD Application (App of Apps pattern)
resource "kubectl_manifest" "root_app" {
  yaml_body = yamlencode({
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    metadata = {
      name      = "root-app"
      namespace = kubernetes_namespace.argocd.metadata[0].name
      finalizers = [
        "resources-finalizer.argocd.argoproj.io"
      ]
    }
    spec = {
      project = "default"
      source = {
        repoURL        = var.git_repository_url
        targetRevision = "main"
        path           = "kubernetes/applications"
        directory = {
          recurse = true
          include = "*.yaml"
        }
      }
      destination = {
        server    = "https://kubernetes.default.svc"
        namespace = kubernetes_namespace.argocd.metadata[0].name
      }
      syncPolicy = {
        automated = {
          prune    = true
          selfHeal = true
        }
        syncOptions = [
          "CreateNamespace=true",
          "PrunePropagationPolicy=foreground",
          "PruneLast=true"
        ]
        retry = {
          limit = 5
          backoff = {
            duration    = "5s"
            factor      = 2
            maxDuration = "3m0s"
          }
        }
      }
    }
  })

  depends_on = [helm_release.argocd]
}

# Create demo application
resource "kubectl_manifest" "demo_app" {
  yaml_body = yamlencode({
    apiVersion = "argoproj.io/v1alpha1"
    kind       = "Application"
    metadata = {
      name      = "demo-guestbook"
      namespace = kubernetes_namespace.argocd.metadata[0].name
    }
    spec = {
      project = "default"
      source = {
        repoURL        = "https://github.com/argoproj/argocd-example-apps.git"
        targetRevision = "HEAD"
        path           = "guestbook"
      }
      destination = {
        server    = "https://kubernetes.default.svc"
        namespace = "demo"
      }
      syncPolicy = {
        automated = {
          prune    = true
          selfHeal = true
        }
        syncOptions = [
          "CreateNamespace=true"
        ]
      }
    }
  })

  depends_on = [helm_release.argocd]
}
