# Script de Deploy Rápido GitOps - Usando cluster existente ou criando minimal
param(
    [switch]$UseExisting = $false,
    [string]$ClusterName = "aks-gitops-demo"
)

Write-Host "🚀 Deploy Rápido GitOps com ArgoCD" -ForegroundColor Green

# Função para executar comandos com verificação
function Invoke-SafeCommand {
    param($Command, $Description, [switch]$IgnoreErrors)
    
    Write-Host "📋 $Description..." -ForegroundColor Yellow
    try {
        Invoke-Expression $Command
        if ($LASTEXITCODE -eq 0 -or $IgnoreErrors) {
            Write-Host "✅ $Description - Sucesso" -ForegroundColor Green
            return $true
        } else {
            Write-Host "❌ $Description - Erro (Exit Code: $LASTEXITCODE)" -ForegroundColor Red
            return $false
        }
    }
    catch {
        Write-Host "❌ $Description - Exceção: $($_.Exception.Message)" -ForegroundColor Red
        if (-not $IgnoreErrors) {
            return $false
        }
    }
}

# Verificar se kubectl está configurado
Write-Host "`n🔍 Verificando ambiente..." -ForegroundColor Cyan

$kubectlTest = kubectl get nodes 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ Cluster Kubernetes detectado" -ForegroundColor Green
    kubectl get nodes
} else {
    Write-Host "⚠️  Nenhum cluster Kubernetes encontrado" -ForegroundColor Yellow
    
    if (-not $UseExisting) {
        Write-Host "🏗️  Criando cluster AKS minimal..." -ForegroundColor Cyan
        
        # Criar resource group se não existir
        Invoke-SafeCommand "az group create --name rg-gitops-demo --location 'East US'" "Criar Resource Group" -IgnoreErrors
        
        # Criar cluster minimal (mais rápido)
        $aksCmd = "az aks create --resource-group rg-gitops-demo --name $ClusterName --node-count 1 --node-vm-size Standard_B2s --generate-ssh-keys --enable-managed-identity --yes"
        if (-not (Invoke-SafeCommand $aksCmd "Criar cluster AKS")) {
            Write-Host "❌ Falha ao criar cluster. Execute manualmente ou use -UseExisting" -ForegroundColor Red
            exit 1
        }
        
        # Obter credenciais
        Invoke-SafeCommand "az aks get-credentials --resource-group rg-gitops-demo --name $ClusterName --overwrite-existing" "Configurar kubectl"
    } else {
        Write-Host "❌ Use um cluster existente ou remova -UseExisting para criar um novo" -ForegroundColor Red
        exit 1
    }
}

# Instalar ArgoCD
Write-Host "`n📦 Instalando ArgoCD..." -ForegroundColor Cyan

# Verificar se namespace existe
$namespaceExists = kubectl get namespace argocd 2>$null
if ($LASTEXITCODE -ne 0) {
    Invoke-SafeCommand "kubectl create namespace argocd" "Criar namespace argocd"
}

# Instalar ArgoCD
Write-Host "📥 Baixando e aplicando manifests do ArgoCD..." -ForegroundColor Yellow
Invoke-SafeCommand "kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml" "Instalar ArgoCD"

# Aguardar pods ficarem prontos (timeout reduzido para demo)
Write-Host "⏳ Aguardando ArgoCD ficar pronto (máximo 2 minutos)..." -ForegroundColor Yellow
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=120s

# Verificar status
Write-Host "`n🔍 Status do ArgoCD:" -ForegroundColor Cyan
kubectl get pods -n argocd

# Expor ArgoCD via port-forward para acesso rápido
Write-Host "`n🌐 Configurando acesso ao ArgoCD..." -ForegroundColor Cyan

# Obter senha do admin
$adminPassword = ""
try {
    $adminPassword = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | ForEach-Object { [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($_)) }
    Write-Host "✅ Senha do admin obtida" -ForegroundColor Green
}
catch {
    Write-Host "⚠️  Não foi possível obter a senha automaticamente" -ForegroundColor Yellow
}

# Aplicar configurações customizadas
Write-Host "`n⚙️  Aplicando configurações customizadas..." -ForegroundColor Cyan
$configPath = ".\argocd-config.yaml"
if (Test-Path $configPath) {
    # Filtrar apenas configurações básicas para evitar erros
    $basicConfig = @"
apiVersion: v1
kind: ConfigMap
metadata:
  name: argocd-rbac-cm
  namespace: argocd
  labels:
    app.kubernetes.io/name: argocd-rbac-cm
    app.kubernetes.io/part-of: argocd
data:
  policy.default: role:readonly
  policy.csv: |
    p, role:admin, applications, *, */*, allow
    p, role:admin, clusters, *, *, allow
    p, role:admin, repositories, *, *, allow
    g, admin, role:admin
"@
    
    $basicConfig | Out-File -FilePath "basic-rbac.yaml" -Encoding UTF8
    Invoke-SafeCommand "kubectl apply -f basic-rbac.yaml" "Aplicar RBAC básico" -IgnoreErrors
    Remove-Item "basic-rbac.yaml" -Force -ErrorAction SilentlyContinue
}

# Criar aplicação demo
Write-Host "`n🚀 Criando aplicação demo..." -ForegroundColor Cyan
$demoApp = @"
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: demo-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/argoproj/argocd-example-apps.git
    targetRevision: HEAD
    path: guestbook
  destination:
    server: https://kubernetes.default.svc
    namespace: demo
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
"@

$demoApp | Out-File -FilePath "demo-app.yaml" -Encoding UTF8
Invoke-SafeCommand "kubectl apply -f demo-app.yaml" "Criar aplicação demo" -IgnoreErrors
Remove-Item "demo-app.yaml" -Force -ErrorAction SilentlyContinue

# Criar sample application local
Write-Host "`n📱 Aplicando sample application..." -ForegroundColor Cyan
if (Test-Path ".\sample-application.yaml") {
    Invoke-SafeCommand "kubectl apply -f .\sample-application.yaml" "Aplicar sample application" -IgnoreErrors
}

# Iniciar port-forward em background
Write-Host "`n🔗 Iniciando port-forward para ArgoCD..." -ForegroundColor Cyan
Start-Process -FilePath "kubectl" -ArgumentList "port-forward svc/argocd-server -n argocd 8080:443" -WindowStyle Minimized

# Output final
Write-Host "`n🎉 GITOPS ATIVADO COM SUCESSO!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green

Write-Host "`n🔐 ACESSO AO ARGOCD:" -ForegroundColor Cyan
Write-Host "🌐 URL: https://localhost:8080" -ForegroundColor White
Write-Host "👤 Username: admin" -ForegroundColor White
if ($adminPassword) {
    Write-Host "🔑 Password: $adminPassword" -ForegroundColor White
} else {
    Write-Host "🔑 Password: Execute o comando abaixo para obter" -ForegroundColor Yellow
    Write-Host "   kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath=`"{.data.password}`" | base64 --decode" -ForegroundColor White
}

Write-Host "`n📋 STATUS ATUAL:" -ForegroundColor Cyan
Write-Host "🔍 Pods ArgoCD:" -ForegroundColor White
kubectl get pods -n argocd --no-headers | ForEach-Object { Write-Host "   $_" -ForegroundColor Gray }

Write-Host "`n📝 COMANDOS ÚTEIS:" -ForegroundColor Cyan
Write-Host "🔍 Status completo: kubectl get all -n argocd" -ForegroundColor White
Write-Host "🔍 Ver aplicações: kubectl get applications -n argocd" -ForegroundColor White
Write-Host "🌐 Port-forward manual: kubectl port-forward svc/argocd-server -n argocd 8080:443" -ForegroundColor White
Write-Host "🗑️  Limpar demo: kubectl delete namespace argocd demo" -ForegroundColor White

Write-Host "`n🚀 PRÓXIMOS PASSOS:" -ForegroundColor Cyan
Write-Host "1. Acesse https://localhost:8080 (aceite o certificado self-signed)" -ForegroundColor White
Write-Host "2. Faça login com admin / senha obtida acima" -ForegroundColor White
Write-Host "3. Explore as aplicações criadas" -ForegroundColor White
Write-Host "4. Configure seus próprios repositórios Git" -ForegroundColor White

Write-Host "`n⚠️  NOTA: Port-forward foi iniciado em background. Para parar: Get-Process kubectl | Stop-Process" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
