# Comandos de Monitoramento GitOps - ArgoCD no AKS

## 🔍 Status do Deployment

```powershell
# Verificar status do Resource Group
az group show --name rg-gitops-demo --output table

# Verificar status do cluster AKS
az aks show --resource-group rg-gitops-demo --name aks-gitops-cluster --output table

# Verificar nodes do cluster
kubectl get nodes -o wide

# Verificar pods do ArgoCD
kubectl get pods -n argocd

# Verificar serviços do ArgoCD
kubectl get svc -n argocd
```

## 🚀 Comandos ArgoCD

```bash
# Listar aplicações
argocd app list

# Ver detalhes de uma aplicação
argocd app get root-app

# Sincronizar aplicação manualmente
argocd app sync root-app

# Ver logs de sincronização
argocd app logs root-app

# Ver diferenças (drift detection)
argocd app diff root-app
```

## 📊 Monitoramento do Cluster

```powershell
# Dashboard do AKS
az aks browse --resource-group rg-gitops-demo --name aks-gitops-cluster

# Verificar utilização de recursos
kubectl top nodes
kubectl top pods --all-namespaces

# Verificar eventos do cluster
kubectl get events --sort-by=.metadata.creationTimestamp

# Verificar logs de um pod específico
kubectl logs -l app=nginx-demo -n demo --tail=100
```

## 🔐 Gerenciamento de Secrets

```powershell
# Verificar External Secrets Operator
kubectl get pods -n external-secrets-system

# Verificar SecretStores
kubectl get secretstores --all-namespaces

# Verificar ExternalSecrets
kubectl get externalsecrets --all-namespaces

# Ver logs do External Secrets
kubectl logs -l app.kubernetes.io/name=external-secrets -n external-secrets-system
```

## 🌐 Acesso às Aplicações

```powershell
# Obter IP do LoadBalancer do ArgoCD
kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Obter IP do NGINX Ingress
kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Port-forward para acesso local (alternativo)
kubectl port-forward svc/argocd-server -n argocd 8080:443

# Testar aplicação demo
kubectl port-forward svc/nginx-demo-service -n demo 8081:80
```

## 🛠️ Troubleshooting

```powershell
# Verificar status de todos os pods
kubectl get pods --all-namespaces | grep -v Running

# Descrever pod com problema
kubectl describe pod <pod-name> -n <namespace>

# Ver logs de pod com erro
kubectl logs <pod-name> -n <namespace> --previous

# Verificar recursos do cluster
kubectl describe nodes

# Verificar limitações de recursos
kubectl describe resourcequota --all-namespaces
```

## 📈 Métricas e Observabilidade

```powershell
# Verificar métricas dos nodes
kubectl top nodes

# Verificar métricas dos pods
kubectl top pods --all-namespaces

# Ver status do HPA
kubectl get hpa --all-namespaces

# Verificar Persistent Volumes
kubectl get pv,pvc --all-namespaces
```

## 🔄 GitOps Workflow

```bash
# Configurar repositório Git no ArgoCD
argocd repo add https://github.com/kcsdevops/Desafio-senior-cloud-engineer.git

# Criar nova aplicação
argocd app create sample-app \
  --repo https://github.com/kcsdevops/Desafio-senior-cloud-engineer.git \
  --path kubernetes/applications \
  --dest-server https://kubernetes.default.svc \
  --dest-namespace demo

# Habilitar auto-sync
argocd app set sample-app --sync-policy automated --auto-prune --self-heal

# Ver histórico de sync
argocd app history sample-app
```

## 🚨 Alerts e Notificações

```powershell
# Configurar Slack notifications (exemplo)
kubectl create secret generic slack-token \
  --from-literal=token=xoxb-your-slack-token \
  -n argocd

# Configurar webhook para GitHub
kubectl create secret generic github-webhook \
  --from-literal=secret=your-webhook-secret \
  -n argocd
```

## 📋 Health Checks

```powershell
# Script de health check completo
function Test-GitOpsHealth {
    Write-Host "🔍 Verificando saúde do GitOps..." -ForegroundColor Cyan
    
    # Verificar ArgoCD
    $argoCDPods = kubectl get pods -n argocd --no-headers | Where-Object { $_ -notmatch "Running" }
    if ($argoCDPods) {
        Write-Host "❌ Pods do ArgoCD com problemas:" -ForegroundColor Red
        $argoCDPods
    } else {
        Write-Host "✅ ArgoCD healthy" -ForegroundColor Green
    }
    
    # Verificar External Secrets
    $esPods = kubectl get pods -n external-secrets-system --no-headers | Where-Object { $_ -notmatch "Running" }
    if ($esPods) {
        Write-Host "❌ External Secrets com problemas:" -ForegroundColor Red
        $esPods
    } else {
        Write-Host "✅ External Secrets healthy" -ForegroundColor Green
    }
    
    # Verificar aplicações
    $apps = argocd app list -o json | ConvertFrom-Json
    foreach ($app in $apps) {
        if ($app.status.health.status -ne "Healthy") {
            Write-Host "❌ Aplicação $($app.metadata.name) não está healthy: $($app.status.health.status)" -ForegroundColor Red
        } else {
            Write-Host "✅ Aplicação $($app.metadata.name) healthy" -ForegroundColor Green
        }
    }
}

# Executar health check
Test-GitOpsHealth
```
