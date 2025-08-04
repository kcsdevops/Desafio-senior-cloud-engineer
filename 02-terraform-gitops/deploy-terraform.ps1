# Deploy AKS GitOps using Terraform
# Script PowerShell para deploy via Terraform

param(
    [string]$Action = "apply",
    [switch]$AutoApprove = $false,
    [string]$VarFile = "terraform.tfvars"
)

Write-Host "🚀 Iniciando deploy GitOps com ArgoCD usando Terraform..." -ForegroundColor Green

# Função para verificar se comando foi executado com sucesso
function Test-CommandSuccess {
    param($Command, $Description)
    
    Write-Host "📋 Executando: $Description" -ForegroundColor Yellow
    Write-Host "🔧 Comando: $Command" -ForegroundColor DarkGray
    
    Invoke-Expression $Command
    
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Erro ao executar: $Description" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ Sucesso: $Description" -ForegroundColor Green
}

# Verificar se Terraform está instalado
Write-Host "`n🔍 ETAPA 1: Verificando dependências" -ForegroundColor Cyan
try {
    $terraformVersion = terraform version
    Write-Host "✅ Terraform encontrado: $terraformVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Terraform não encontrado. Instale o Terraform primeiro." -ForegroundColor Red
    Write-Host "💡 Baixe em: https://www.terraform.io/downloads.html" -ForegroundColor Yellow
    exit 1
}

# Verificar se Azure CLI está instalado e logado
try {
    $azVersion = az version --query '"azure-cli"' -o tsv
    Write-Host "✅ Azure CLI encontrado: $azVersion" -ForegroundColor Green
    
    $currentUser = az account show --query user.name -o tsv 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Usuário logado no Azure: $currentUser" -ForegroundColor Green
    } else {
        Write-Host "❌ Não está logado no Azure. Execute 'az login' primeiro." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "❌ Azure CLI não encontrado. Instale o Azure CLI primeiro." -ForegroundColor Red
    exit 1
}

# Verificar se kubectl está instalado
try {
    $kubectlVersion = kubectl version --client --short 2>$null
    Write-Host "✅ kubectl encontrado" -ForegroundColor Green
} catch {
    Write-Host "⚠️  kubectl não encontrado. Será instalado automaticamente pelo Terraform." -ForegroundColor Yellow
}

# Verificar se Helm está instalado
try {
    $helmVersion = helm version --short 2>$null
    Write-Host "✅ Helm encontrado" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Helm não encontrado. Instale o Helm para comandos manuais." -ForegroundColor Yellow
    Write-Host "💡 Execute: choco install kubernetes-helm" -ForegroundColor Yellow
}

# Navegar para o diretório terraform
$terraformDir = Join-Path $PSScriptRoot "terraform"
if (-not (Test-Path $terraformDir)) {
    Write-Host "❌ Diretório terraform não encontrado: $terraformDir" -ForegroundColor Red
    exit 1
}

Set-Location $terraformDir
Write-Host "📁 Navegando para: $terraformDir" -ForegroundColor DarkGray

# Verificar se arquivo de variáveis existe
$varFilePath = Join-Path $terraformDir $VarFile
if (-not (Test-Path $varFilePath)) {
    Write-Host "📝 Arquivo de variáveis não encontrado. Criando $VarFile..." -ForegroundColor Yellow
    
    $exampleFile = Join-Path $terraformDir "terraform.tfvars.example"
    if (Test-Path $exampleFile) {
        Copy-Item $exampleFile $varFilePath
        Write-Host "✅ Arquivo $VarFile criado baseado no exemplo" -ForegroundColor Green
    } else {
        Write-Host "❌ Arquivo de exemplo não encontrado: $exampleFile" -ForegroundColor Red
        exit 1
    }
}

# 2. Inicializar Terraform
Write-Host "`n🔧 ETAPA 2: Inicializando Terraform" -ForegroundColor Cyan
Test-CommandSuccess "terraform init -upgrade" "Inicializar Terraform"

# 3. Validar configuração
Write-Host "`n✅ ETAPA 3: Validando configuração" -ForegroundColor Cyan
Test-CommandSuccess "terraform validate" "Validar configuração Terraform"

# 4. Formatar código
Write-Host "`n🎨 ETAPA 4: Formatando código" -ForegroundColor Cyan
Test-CommandSuccess "terraform fmt -recursive" "Formatar código Terraform"

# 5. Planejar execução
Write-Host "`n📋 ETAPA 5: Planejando execução" -ForegroundColor Cyan
Test-CommandSuccess "terraform plan -var-file=`"$VarFile`" -out=tfplan" "Criar plano de execução"

if ($Action -eq "plan") {
    Write-Host "`n🎉 PLANEJAMENTO CONCLUÍDO!" -ForegroundColor Green
    Write-Host "📄 Plano salvo em: tfplan" -ForegroundColor White
    Write-Host "🚀 Para aplicar: .\deploy-terraform.ps1 -Action apply -AutoApprove" -ForegroundColor Yellow
    exit 0
}

# 6. Aplicar mudanças
Write-Host "`n🚀 ETAPA 6: Aplicando mudanças" -ForegroundColor Cyan

if ($Action -eq "apply") {
    if ($AutoApprove) {
        Test-CommandSuccess "terraform apply -auto-approve tfplan" "Aplicar mudanças automaticamente"
    } else {
        Write-Host "⚠️  Prestes a aplicar as mudanças. Confirme:" -ForegroundColor Yellow
        Test-CommandSuccess "terraform apply tfplan" "Aplicar mudanças"
    }
} elseif ($Action -eq "destroy") {
    Write-Host "⚠️  ATENÇÃO: Isso destruirá todos os recursos!" -ForegroundColor Red
    if ($AutoApprove) {
        Test-CommandSuccess "terraform destroy -var-file=`"$VarFile`" -auto-approve" "Destruir recursos"
    } else {
        Test-CommandSuccess "terraform destroy -var-file=`"$VarFile`"" "Destruir recursos"
    }
} else {
    Write-Host "❌ Ação inválida: $Action. Use 'plan', 'apply' ou 'destroy'" -ForegroundColor Red
    exit 1
}

# 7. Obter outputs importantes
if ($Action -eq "apply") {
    Write-Host "`n📊 ETAPA 7: Obtendo informações do cluster" -ForegroundColor Cyan
    
    try {
        Write-Host "📋 Obtendo outputs do Terraform..." -ForegroundColor Yellow
        $outputs = terraform output -json | ConvertFrom-Json
        
        # Configurar kubectl
        $resourceGroup = $outputs.resource_group_name.value
        $clusterName = $outputs.aks_cluster_name.value
        
        Write-Host "`n🔑 Configurando kubectl..." -ForegroundColor Yellow
        Test-CommandSuccess "az aks get-credentials --resource-group $resourceGroup --name $clusterName --overwrite-existing" "Configurar kubectl"
        
        # Verificar conectividade
        Write-Host "`n🔍 Verificando conectividade do cluster..." -ForegroundColor Yellow
        Test-CommandSuccess "kubectl get nodes" "Verificar nodes do cluster"
        
        # Aguardar ArgoCD ficar pronto
        Write-Host "`n⏳ Aguardando ArgoCD ficar pronto..." -ForegroundColor Yellow
        kubectl wait --for=condition=Ready pods --all -n argocd --timeout=600s
        
        # Obter IP do LoadBalancer do ArgoCD
        Write-Host "`n🌐 Obtendo IP do ArgoCD..." -ForegroundColor Yellow
        $maxAttempts = 30
        $attempt = 0
        
        do {
            $external_ip = kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>$null
            if ([string]::IsNullOrEmpty($external_ip)) {
                $attempt++
                Start-Sleep -Seconds 10
                Write-Host "." -NoNewline -ForegroundColor Yellow
            }
        } while ([string]::IsNullOrEmpty($external_ip) -and $attempt -lt $maxAttempts)
        
        Write-Host ""
        
        if (-not [string]::IsNullOrEmpty($external_ip)) {
            Write-Host "✅ ArgoCD disponível em: http://$external_ip" -ForegroundColor Green
        } else {
            Write-Host "⚠️  IP externo ainda não disponível. Use port-forward:" -ForegroundColor Yellow
            Write-Host "   kubectl port-forward svc/argocd-server -n argocd 8080:80" -ForegroundColor White
        }
        
        # Obter senha do admin
        $admin_password = kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>$null
        if (-not [string]::IsNullOrEmpty($admin_password)) {
            $admin_password = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($admin_password))
        } else {
            $admin_password = $outputs.argocd_admin_password.value
        }
        
    } catch {
        Write-Host "⚠️  Erro ao obter informações do cluster. Verifique manualmente." -ForegroundColor Yellow
        $external_ip = "N/A"
        $admin_password = "Veja terraform output argocd_admin_password"
    }
    
    # Output final
    Write-Host "`n🎉 DEPLOY CONCLUÍDO COM SUCESSO!" -ForegroundColor Green
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
    
    Write-Host "`n📋 INFORMAÇÕES DO CLUSTER:" -ForegroundColor Cyan
    Write-Host "🏷️  Resource Group: $resourceGroup" -ForegroundColor White
    Write-Host "🏷️  Cluster Name: $clusterName" -ForegroundColor White
    Write-Host "🌍 OIDC Issuer: $($outputs.oidc_issuer_url.value)" -ForegroundColor White
    
    Write-Host "`n🔐 ACESSO AO ARGOCD:" -ForegroundColor Cyan
    if (-not [string]::IsNullOrEmpty($external_ip) -and $external_ip -ne "N/A") {
        Write-Host "🌐 URL: http://$external_ip" -ForegroundColor White
    } else {
        Write-Host "🌐 URL: Use port-forward ou aguarde LoadBalancer" -ForegroundColor White
    }
    Write-Host "👤 Username: admin" -ForegroundColor White
    Write-Host "🔑 Password: $admin_password" -ForegroundColor White
    
    Write-Host "`n📝 COMANDOS ÚTEIS:" -ForegroundColor Cyan
    Write-Host "🔍 Ver pods ArgoCD: kubectl get pods -n argocd" -ForegroundColor White
    Write-Host "🔍 Ver aplicações: kubectl get applications -n argocd" -ForegroundColor White
    Write-Host "🔄 Port-forward: kubectl port-forward svc/argocd-server -n argocd 8080:80" -ForegroundColor White
    Write-Host "📊 Dashboard: az aks browse --resource-group $resourceGroup --name $clusterName" -ForegroundColor White
    Write-Host "🗂️  Ver outputs: terraform output" -ForegroundColor White
    
    Write-Host "`n🚀 PRÓXIMOS PASSOS:" -ForegroundColor Cyan
    Write-Host "1. Acesse a interface web do ArgoCD usando as credenciais acima" -ForegroundColor White
    Write-Host "2. Verifique as aplicações implantadas automaticamente" -ForegroundColor White
    Write-Host "3. Configure repositórios Git adicionais se necessário" -ForegroundColor White
    Write-Host "4. Monitore os logs: kubectl logs -n argocd -l app.kubernetes.io/name=argocd-server" -ForegroundColor White
    
    Write-Host "`n💡 DICA: Use 'terraform output' para ver todas as informações!" -ForegroundColor Yellow
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
}

Write-Host "`n🎯 Execução concluída!" -ForegroundColor Green
