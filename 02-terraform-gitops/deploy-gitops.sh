#!/bin/bash
# Deploy GitOps com ArgoCD no AKS

set -e

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Iniciando deploy GitOps com ArgoCD no AKS...${NC}"

# Verificar se kubectl está configurado
echo -e "\n${CYAN}🔍 Verificando ambiente...${NC}"

if kubectl get nodes > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Cluster Kubernetes detectado${NC}"
    kubectl get nodes
else
    echo -e "${YELLOW}⚠️  Nenhum cluster Kubernetes encontrado${NC}"
    echo -e "${CYAN}🏗️  Criando cluster AKS minimal...${NC}"
    
    # Criar resource group
    echo -e "${YELLOW}📋 Criando Resource Group...${NC}"
    az group create --name rg-gitops-demo --location "East US" || true
    
    # Criar cluster AKS
    echo -e "${YELLOW}📋 Criando cluster AKS (isso pode levar alguns minutos)...${NC}"
    az aks create \
        --resource-group rg-gitops-demo \
        --name aks-gitops-demo \
        --node-count 1 \
        --node-vm-size Standard_B2s \
        --generate-ssh-keys \
        --enable-managed-identity \
        --yes
    
    # Obter credenciais
    echo -e "${YELLOW}📋 Configurando kubectl...${NC}"
    az aks get-credentials --resource-group rg-gitops-demo --name aks-gitops-demo --overwrite-existing
fi

# Instalar ArgoCD
echo -e "\n${CYAN}📦 Instalando ArgoCD...${NC}"

# Criar namespace se não existir
kubectl create namespace argocd || true

# Instalar ArgoCD
echo -e "${YELLOW}📥 Instalando ArgoCD...${NC}"
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml

# Aguardar pods ficarem prontos
echo -e "${YELLOW}⏳ Aguardando ArgoCD ficar pronto (máximo 3 minutos)...${NC}"
kubectl wait --for=condition=Ready pods --all -n argocd --timeout=180s

# Verificar status
echo -e "\n${CYAN}🔍 Status do ArgoCD:${NC}"
kubectl get pods -n argocd

# Configurar acesso
echo -e "\n${CYAN}🌐 Configurando acesso ao ArgoCD...${NC}"

# Patch para LoadBalancer
echo -e "${YELLOW}📋 Expondo ArgoCD via LoadBalancer...${NC}"
kubectl patch svc argocd-server -n argocd -p '{"spec":{"type":"LoadBalancer"}}'

# Obter senha do admin
echo -e "${YELLOW}📋 Obtendo senha do admin...${NC}"
ADMIN_PASSWORD=$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" | base64 -d)

# Aguardar LoadBalancer obter IP
echo -e "${YELLOW}⏳ Aguardando LoadBalancer obter IP externo...${NC}"
for i in {1..30}; do
    EXTERNAL_IP=$(kubectl get svc argocd-server -n argocd -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || echo "")
    if [ -n "$EXTERNAL_IP" ]; then
        break
    fi
    echo -n "."
    sleep 10
done
echo ""

# Aplicar configuração RBAC básica
echo -e "\n${CYAN}⚙️  Aplicando configurações básicas...${NC}"
cat << EOF | kubectl apply -f -
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
EOF

# Criar aplicação demo
echo -e "\n${CYAN}🚀 Criando aplicação demo...${NC}"
cat << EOF | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: demo-guestbook
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
EOF

# Criar aplicação sample local se existir
if [ -f "sample-application.yaml" ]; then
    echo -e "${YELLOW}📱 Aplicando sample application...${NC}"
    kubectl apply -f sample-application.yaml || true
fi

# Instalar ArgoCD CLI
echo -e "\n${CYAN}🛠️  Instalando ArgoCD CLI...${NC}"
if ! command -v argocd &> /dev/null; then
    echo -e "${YELLOW}📥 Baixando ArgoCD CLI...${NC}"
    curl -sSL -o /tmp/argocd https://github.com/argoproj/argo-cd/releases/latest/download/argocd-linux-amd64
    chmod +x /tmp/argocd
    sudo mv /tmp/argocd /usr/local/bin/argocd
fi

# Output final
echo -e "\n${GREEN}🎉 GITOPS ATIVADO COM SUCESSO!${NC}"
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -e "\n${CYAN}🔐 ACESSO AO ARGOCD:${NC}"
if [ -n "$EXTERNAL_IP" ]; then
    echo -e "${WHITE}🌐 URL: http://$EXTERNAL_IP${NC}"
else
    echo -e "${YELLOW}🌐 URL: Aguardando LoadBalancer (execute: kubectl get svc argocd-server -n argocd)${NC}"
fi
echo -e "${WHITE}👤 Username: admin${NC}"
echo -e "${WHITE}🔑 Password: $ADMIN_PASSWORD${NC}"

echo -e "\n${CYAN}📋 STATUS ATUAL:${NC}"
echo -e "${WHITE}🔍 Pods ArgoCD:${NC}"
kubectl get pods -n argocd --no-headers

echo -e "\n${CYAN}📝 COMANDOS ÚTEIS:${NC}"
echo -e "${WHITE}🔍 Status completo: kubectl get all -n argocd${NC}"
echo -e "${WHITE}🔍 Ver aplicações: kubectl get applications -n argocd${NC}"
echo -e "${WHITE}🌐 Port-forward: kubectl port-forward svc/argocd-server -n argocd 8080:443${NC}"
echo -e "${WHITE}🗑️  Limpar demo: kubectl delete namespace argocd demo${NC}"

echo -e "\n${CYAN}🚀 PRÓXIMOS PASSOS:${NC}"
echo -e "${WHITE}1. Acesse a URL do ArgoCD mostrada acima${NC}"
echo -e "${WHITE}2. Faça login com admin e a senha obtida${NC}"
echo -e "${WHITE}3. Explore as aplicações criadas automaticamente${NC}"
echo -e "${WHITE}4. Configure seus próprios repositórios Git${NC}"

# Login no ArgoCD CLI se possível
if [ -n "$EXTERNAL_IP" ]; then
    echo -e "\n${CYAN}🔐 Configurando ArgoCD CLI...${NC}"
    argocd login $EXTERNAL_IP --username admin --password $ADMIN_PASSWORD --insecure || true
    
    echo -e "\n${CYAN}📱 Listando aplicações:${NC}"
    argocd app list || true
fi

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}✅ GitOps com ArgoCD configurado com sucesso!${NC}"
