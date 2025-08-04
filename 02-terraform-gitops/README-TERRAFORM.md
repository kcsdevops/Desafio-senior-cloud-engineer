# Deploy GitOps AKS com Terraform

Esta implementação usa **Terraform** para provisionar um cluster AKS completo com GitOps usando ArgoCD, demonstrando infraestrutura como código seguindo as melhores práticas para Senior Cloud Engineer.

## 🏗️ Arquitetura Implantada

```
Azure Subscription
├── Resource Group (rg-gitops-demo)
├── Virtual Network (10.0.0.0/8)
│   └── AKS Subnet (10.240.0.0/16)
├── AKS Cluster
│   ├── System Node Pool (Standard_B2s, auto-scaling 1-5)
│   ├── Workload Identity & OIDC
│   ├── Azure AD RBAC
│   └── Log Analytics Integration
└── Managed Identities
    ├── AKS Cluster Identity
    └── ArgoCD Workload Identity
```

### 🚀 Componentes Kubernetes Instalados

- **ArgoCD** - GitOps controller com interface web
- **External Secrets Operator** - Gerenciamento seguro de secrets
- **NGINX Ingress Controller** - Proxy reverso e balanceamento
- **cert-manager** - Certificados SSL automatizados
- **Aplicações Demo** - Guestbook e root app (App of Apps pattern)

## 📋 Pré-requisitos

### Ferramentas Obrigatórias
- **Terraform** >= 1.0 ([Download](https://www.terraform.io/downloads.html))
- **Azure CLI** >= 2.50 ([Download](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli))
- **kubectl** >= 1.28 ([Download](https://kubernetes.io/docs/tools/install-kubectl/))

### Ferramentas Opcionais
- **Helm** >= 3.12 (para comandos manuais)
- **PowerShell** >= 7.0 (para scripts Windows)

### Permissões Azure
- **Contributor** ou **Owner** na subscription
- Permissões para criar Service Principals (se usando OIDC)

## 🚀 Deploy Rápido

### 1. Autenticação Azure
```powershell
# Login no Azure
az login

# Verificar subscription ativa
az account show

# Trocar subscription se necessário
az account set --subscription "sua-subscription-id"
```

### 2. Configurar Variáveis
```powershell
# Copiar arquivo de exemplo
cd terraform
Copy-Item terraform.tfvars.example terraform.tfvars

# Editar variáveis conforme necessário
notepad terraform.tfvars
```

### 3. Deploy Completo (Automático)
```powershell
# Executar script de deploy
.\deploy-terraform.ps1 -AutoApprove

# Ou apenas planejar primeiro
.\deploy-terraform.ps1 -Action plan
```

### 4. Deploy Manual (Passo a Passo)
```powershell
cd terraform

# Inicializar Terraform
terraform init

# Planejar mudanças
terraform plan -var-file="terraform.tfvars"

# Aplicar mudanças
terraform apply -var-file="terraform.tfvars"
```

## ⚙️ Configurações Personalizáveis

### terraform.tfvars
```hcl
# Configuração básica do cluster
resource_group_name = "rg-gitops-demo"
location           = "East US"
cluster_name       = "aks-gitops-cluster"
kubernetes_version = "1.28.5"

# Configuração dos nodes
node_count    = 2
node_vm_size  = "Standard_B2s"  # ou Standard_D2s_v3 para produção

# ArgoCD
argocd_admin_password = "SuaSenhaSegura123!"
domain_name          = "seu-dominio.com"

# Repositório Git
git_repository_url = "https://github.com/seu-usuario/seu-repo.git"

# Tags
tags = {
  Environment = "production"
  Project     = "gitops"
  Owner       = "seu-nome"
}
```

## 📊 Outputs e Informações

Após o deploy, o Terraform fornece outputs importantes:

```powershell
# Ver todos os outputs
terraform output

# Outputs específicos
terraform output argocd_url
terraform output kube_config
terraform output useful_commands
```

### Comandos Úteis Gerados
```bash
# Configurar kubectl
az aks get-credentials --resource-group rg-gitops-demo --name aks-gitops-cluster

# Acessar ArgoCD (port-forward)
kubectl port-forward svc/argocd-server -n argocd 8080:80

# Ver aplicações ArgoCD
kubectl get applications -n argocd

# Dashboard Kubernetes
az aks browse --resource-group rg-gitops-demo --name aks-gitops-cluster
```

## 🔐 Acesso ao ArgoCD

### Opção 1: LoadBalancer (IP Público)
```powershell
# Obter IP público
kubectl get svc argocd-server -n argocd

# Acessar: http://IP_PUBLICO
# Username: admin
# Password: (definida em terraform.tfvars)
```

### Opção 2: Port Forward (Local)
```powershell
# Port forward
kubectl port-forward svc/argocd-server -n argocd 8080:80

# Acessar: http://localhost:8080
# Username: admin
# Password: (definida em terraform.tfvars)
```

### Opção 3: Ingress (com domínio)
```powershell
# Configurar DNS para apontar para NGINX Ingress IP
kubectl get svc ingress-nginx-controller -n ingress-nginx

# Acessar: https://argocd.seu-dominio.com
```

## 🔄 Gerenciamento GitOps

### Estrutura de Repositório Esperada
```
seu-repositorio/
├── kubernetes/
│   └── applications/
│       ├── app1.yaml
│       ├── app2.yaml
│       └── environments/
│           ├── dev/
│           ├── staging/
│           └── prod/
└── charts/
    ├── app1/
    └── app2/
```

### Exemplo de Application ArgoCD
```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/seu-usuario/seu-repo.git
    targetRevision: main
    path: kubernetes/my-app
  destination:
    server: https://kubernetes.default.svc
    namespace: my-app
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

## 🛠️ Troubleshooting

### Problemas Comuns

#### 1. Erro de Permissões Azure
```powershell
# Verificar permissões
az role assignment list --assignee $(az account show --query user.name -o tsv)

# Solicitar permissões de Contributor/Owner
```

#### 2. ArgoCD Pods não Iniciam
```powershell
# Verificar pods
kubectl get pods -n argocd

# Ver logs
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server

# Verificar recursos
kubectl describe pods -n argocd
```

#### 3. LoadBalancer sem IP Externo
```powershell
# Verificar serviço
kubectl get svc -n argocd argocd-server

# Verificar eventos
kubectl get events -n argocd --sort-by='.lastTimestamp'

# Usar port-forward como alternativa
kubectl port-forward svc/argocd-server -n argocd 8080:80
```

#### 4. Problemas de Conectividade
```powershell
# Verificar nodes
kubectl get nodes

# Verificar network policy
kubectl get networkpolicies --all-namespaces

# Testar DNS
kubectl run test-pod --image=busybox -it --rm -- nslookup kubernetes.default
```

### Logs Importantes
```powershell
# ArgoCD Server
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server -f

# ArgoCD Application Controller
kubectl logs -n argocd -l app.kubernetes.io/name=argocd-application-controller -f

# External Secrets
kubectl logs -n external-secrets-system -l app.kubernetes.io/name=external-secrets -f

# NGINX Ingress
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx -f
```

## 🗂️ Estrutura de Arquivos

```
02-terraform-gitops/
├── terraform/
│   ├── main.tf              # Configuração principal
│   ├── variables.tf         # Definição de variáveis
│   ├── outputs.tf           # Outputs do Terraform
│   └── terraform.tfvars.example  # Exemplo de configuração
├── deploy-terraform.ps1     # Script de deploy
├── argocd-config.yaml      # Configurações ArgoCD extras
├── external-secrets-config.yaml  # Config External Secrets
└── README-TERRAFORM.md     # Esta documentação
```

## 🧹 Limpeza/Destruição

### Remover Todos os Recursos
```powershell
# Via script
.\deploy-terraform.ps1 -Action destroy -AutoApprove

# Via Terraform direto
cd terraform
terraform destroy -var-file="terraform.tfvars" -auto-approve
```

### Remover Apenas ArgoCD
```powershell
# Remover namespace ArgoCD
kubectl delete namespace argocd

# Manter cluster AKS
```

## 💰 Estimativa de Custos

### Recursos Principais (East US)
- **AKS Cluster**: ~$0.10/hora (management fee)
- **2x Standard_B2s VMs**: ~$0.083/hora cada = $0.166/hora
- **Load Balancers**: ~$0.025/hora cada (2x) = $0.05/hora
- **Log Analytics**: ~$2.30/GB ingerido
- **Public IPs**: ~$0.005/hora cada

**Total Estimado**: ~$0.32/hora = ~$230/mês

### Otimizações de Custo
- Use **Standard_B1s** para demos ($0.041/hora)
- Configure **auto-shutdown** em ambientes de desenvolvimento
- Use **Azure Dev/Test** pricing se elegível
- Configure **retention policies** para logs

## 🔗 Links Úteis

- [Terraform AzureRM Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest)
- [ArgoCD Documentation](https://argo-cd.readthedocs.io/)
- [AKS Best Practices](https://docs.microsoft.com/en-us/azure/aks/best-practices)
- [External Secrets Operator](https://external-secrets.io/)
- [NGINX Ingress Controller](https://kubernetes.github.io/ingress-nginx/)

---

## 🎯 Status do Projeto

✅ **Completo** - Infraestrutura como código com Terraform  
✅ **Testado** - Deploy automatizado funcionando  
✅ **Documentado** - Guia completo para reprodução  
✅ **Seguro** - RBAC, Workload Identity, Network Policies  
✅ **Observável** - Logs centralizados, métricas integradas  

**Próximos Passos**: Integrar com Azure Key Vault, configurar alertas, implementar backup automatizado.
