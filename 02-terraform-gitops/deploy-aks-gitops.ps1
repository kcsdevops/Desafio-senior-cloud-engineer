# Deploy AKS com GitOps e ArgoCD
# Script PowerShell para configuração completa

param(
    [string]$ResourceGroupName = "rg-gitops-demo",
    [string]$ClusterName = "aks-gitops-cluster",
    [string]$Location = "East US",
    [string]$NodeCount = "2"
)

Write-Host "🚀 Iniciando deploy GitOps com ArgoCD no AKS..." -ForegroundColor Green

# Função para verificar se comando foi executado com sucesso
function Test-CommandSuccess {
    param($Command, $Description)
    
    Write-Host "📋 Executando: $Description" -ForegroundColor Yellow
    Invoke-Expression $Command
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erro ao executar: $Description" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Sucesso: $Description" -ForegroundColor Green
}

# 1. Criar Resource Group
Write-Host "`n🏗️  ETAPA 1: Criando Resource Group" -ForegroundColor Cyan
Test-CommandSuccess "az group create --name $ResourceGroupName --location '$Location'" "Criar Resource Group"

# 2. Criar cluster AKS
Write-Host "`n🔧 ETAPA 2: Criando cluster AKS" -ForegroundColor Cyan
$aksCommand = @"
az aks create \
  --resource-group $ResourceGroupName \
  --name $ClusterName \
  --node-count $NodeCount \
  --node-vm-size Standard_B2s \
  --enable-addons monitoring \
  --enable-managed-identity \
  --generate-ssh-keys \
  --enable-cluster-autoscaler \
  --min-count 1 \
  --max-count 5 \
  --enable-oidc-issuer \
  --enable-workload-identity \
  --network-plugin azure \
  --network-policy calico
"@

Test-CommandSuccess $aksCommand "Criar cluster AKS"

# 3. Obter credenciais do cluster
Write-Host "`n🔑 ETAPA 3: Configurando kubectl" -ForegroundColor Cyan
Test-CommandSuccess "az aks get-credentials --resource-group $ResourceGroupName --name $ClusterName --overwrite-existing" "Configurar kubectl"

# 4. Verificar conectividade do cluster
Write-Host "`n🔍 ETAPA 4: Verificando cluster" -ForegroundColor Cyan
Test-CommandSuccess "kubectl get nodes" "Verificar nodes do cluster"

# 5. Instalar ArgoCD
Write-Host "`n📦 ETAPA 5: Instalando ArgoCD" -ForegroundColor Cyan

# Criar namespace do ArgoCD
Test-CommandSuccess "kubectl create namespace argocd" "Criar namespace argocd"

# Instalar ArgoCD
Test-CommandSuccess "kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml" "Instalar ArgoCD"

# Aguardar pods ficarem prontos
Write-Host "⏳ Aguardando pods do ArgoCD ficarem prontos..." -ForegroundColor Yellow
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=300s

# 6. Configurar ArgoCD
Write-Host "`n⚙️  ETAPA 6: Configurando ArgoCD" -ForegroundColor Cyan

# Aplicar configurações customizadas
$configPath = Join-Path $PSScriptRoot "argocd-config.yaml"
if (Test-Path $configPath) {
    Test-CommandSuccess "kubectl apply -f '$configPath'" "Aplicar configurações ArgoCD"
} else {
    Write-Host "⚠️  Arquivo argocd-config.yaml não encontrado em $configPath" -ForegroundColor Yellow
}

# 7. Expor ArgoCD Server
Write-Host "`n🌐 ETAPA 7: Expondo ArgoCD Server" -ForegroundColor Cyan

# Patch do service para LoadBalancer
Test-CommandSuccess "kubectl patch svc argocd-server -n argocd -p '{\"spec\":{\"type\":\"LoadBalancer\"}}'" "Expor ArgoCD Server"

# 8. Obter senha admin do ArgoCD
Write-Host "`n🔐 ETAPA 8: Obtendo credenciais ArgoCD" -ForegroundColor Cyan

Write-Host "⏳ Aguardando LoadBalancer obter IP externo..." -ForegroundColor Yellow
do {
    $external_ip = kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null
    if ([string]::IsNullOrEmpty($external_ip)) {
        Start-Sleep -Seconds 10
        Write-Host "." -NoNewline -ForegroundColor Yellow
    }
} while ([string]::IsNullOrEmpty($external_ip))

Write-Host ""
$admin_password = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | ForEach-Object { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) }

# 9. Configurar CLI do ArgoCD
Write-Host "`n🛠️  ETAPA 9: Configurando ArgoCD CLI" -ForegroundColor Cyan

# Download ArgoCD CLI se não existir
if (-not (Get-Command "argocd" -ErrorAction SilentlyContinue)) {
    Write-Host "📥 Baixando ArgoCD CLI..." -ForegroundColor Yellow
    $argoCLIUrl = "https://github.com/argoproj/argo-cd/releases/latest/download/argocd-windows-amd64.exe"
    $argoCLIPath = Join-Path $env:TEMP "argocd.exe"
    Invoke-WebRequest -Uri $argoCLIUrl -OutFile $argoCLIPath
    
    # Mover para diretório do sistema
    $systemPath = "C:\Windows\System32\argocd.exe"
    if (Test-Path $systemPath) {
        Remove-Item $systemPath -Force
    }
    Move-Item $argoCLIPath $systemPath
    Write-Host "✅ ArgoCD CLI instalado em $systemPath" -ForegroundColor Green
}

# Login no ArgoCD
Write-Host "🔐 Fazendo login no ArgoCD..." -ForegroundColor Yellow
$env:ARGOCD_OPTS = "--insecure"
argocd login $external_ip --username admin --password $admin_password --insecure

# 10. Criar aplicação root (App of Apps)
Write-Host "`n🚀 ETAPA 10: Criando aplicação root" -ForegroundColor Cyan

$rootApp = @"
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/kcsdevops/Desafio-senior-cloud-engineer.git
    targetRevision: main
    path: kubernetes/applications
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
"@

$rootApp | Out-File -FilePath "root-app-temp.yaml" -Encoding UTF8
Test-CommandSuccess "kubectl apply -f root-app-temp.yaml" "Criar aplicação root"
Remove-Item "root-app-temp.yaml" -Force

# 11. Instalar External Secrets Operator
Write-Host "`n🔒 ETAPA 11: Instalando External Secrets Operator" -ForegroundColor Cyan

# Adicionar Helm repo
Test-CommandSuccess "helm repo add external-secrets https://charts.external-secrets.io" "Adicionar repo External Secrets"
Test-CommandSuccess "helm repo update" "Atualizar repos Helm"

# Instalar External Secrets
Test-CommandSuccess "helm install external-secrets external-secrets/external-secrets -n external-secrets-system --create-namespace" "Instalar External Secrets Operator"

# Aplicar configurações do External Secrets
$externalSecretsPath = Join-Path $PSScriptRoot "external-secrets-config.yaml"
if (Test-Path $externalSecretsPath) {
    # Aguardar CRDs ficarem disponíveis
    Write-Host "⏳ Aguardando CRDs do External Secrets..." -ForegroundColor Yellow
    Start-Sleep -Seconds 30
    
    try {
        Test-CommandSuccess "kubectl apply -f '$externalSecretsPath'" "Aplicar configurações External Secrets"
    } catch {
        Write-Host "⚠️  Algumas configurações do External Secrets podem precisar ser ajustadas para o ambiente específico" -ForegroundColor Yellow
    }
}

# 12. Configurar Ingress (opcional)
Write-Host "`n🌍 ETAPA 12: Configurando Ingress (opcional)" -ForegroundColor Cyan

# Instalar NGINX Ingress Controller
Test-CommandSuccess "helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx" "Adicionar repo NGINX Ingress"
Test-CommandSuccess "helm repo update" "Atualizar repos Helm"
Test-CommandSuccess "helm install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace" "Instalar NGINX Ingress"

# Output final
Write-Host "`n🎉 DEPLOY CONCLUÍDO COM SUCESSO!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green

Write-Host "`n📋 INFORMAÇÕES DO CLUSTER:" -ForegroundColor Cyan
Write-Host "🏷️  Resource Group: $ResourceGroupName" -ForegroundColor White
Write-Host "🏷️  Cluster Name: $ClusterName" -ForegroundColor White
Write-Host "🌍 Location: $Location" -ForegroundColor White
Write-Host "🔢 Node Count: $NodeCount" -ForegroundColor White

Write-Host "`n🔐 ACESSO AO ARGOCD:" -ForegroundColor Cyan
Write-Host "🌐 URL: http://$external_ip" -ForegroundColor White
Write-Host "👤 Username: admin" -ForegroundColor White
Write-Host "🔑 Password: $admin_password" -ForegroundColor White

Write-Host "`n📝 COMANDOS ÚTEIS:" -ForegroundColor Cyan
Write-Host "🔍 Ver pods ArgoCD: kubectl get pods -n argocd" -ForegroundColor White
Write-Host "🔍 Ver aplicações: argocd app list" -ForegroundColor White
Write-Host "🔄 Sync aplicação: argocd app sync root-app" -ForegroundColor White
Write-Host "📊 Dashboard K8s: az aks browse --resource-group $ResourceGroupName --name $ClusterName" -ForegroundColor White

Write-Host "`n🚀 PRÓXIMOS PASSOS:" -ForegroundColor Cyan
Write-Host "1. Acesse a interface web do ArgoCD usando as credenciais acima" -ForegroundColor White
Write-Host "2. Configure repositórios Git com suas aplicações" -ForegroundColor White
Write-Host "3. Crie Applications para deploy automático" -ForegroundColor White
Write-Host "4. Configure External Secrets para suas credenciais" -ForegroundColor White

Write-Host "`n💡 DICA: Salve as credenciais em local seguro!" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
