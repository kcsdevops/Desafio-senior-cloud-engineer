# Terraform & GitOps

## 1. Módulo Terraform EKS com Autoscaling

### Estrutura do Módulo

```
modules/eks-cluster/
├── main.tf                 # Recursos principais
├── variables.tf            # Variáveis de entrada
├── outputs.tf             # Outputs do módulo
├── versions.tf            # Versões e providers
└── README.md              # Documentação
```

### Características do Módulo

✅ **EKS Cluster**: Configuração completa com versioning  
✅ **Node Groups**: Auto Scaling com múltiplas AZs  
✅ **IAM Roles**: Service Account integration  
✅ **Security**: VPC, Security Groups, RBAC  
✅ **Addons**: CNI, CoreDNS, kube-proxy  
✅ **Monitoring**: CloudWatch integration  

### Utilização

```hcl
module "eks_cluster" {
  source = "./modules/eks-cluster"
  
  cluster_name    = "production-eks"
  cluster_version = "1.27"
  
  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnet_ids
  
  node_groups = {
    general = {
      desired_size = 2
      max_size     = 10
      min_size     = 1
      instance_types = ["t3.medium"]
    }
    
    compute = {
      desired_size = 1
      max_size     = 5
      min_size     = 0
      instance_types = ["c5.large"]
      taints = [{
        key    = "workload"
        value  = "compute-intensive"
        effect = "NO_SCHEDULE"
      }]
    }
  }
  
  enable_irsa = true
  service_accounts = {
    "aws-load-balancer-controller" = {
      namespace = "kube-system"
      policies  = ["arn:aws:iam::aws:policy/ElasticLoadBalancingFullAccess"]
    }
    "external-dns" = {
      namespace = "external-dns"
      policies  = ["arn:aws:iam::aws:policy/Route53FullAccess"]
    }
  }
  
  tags = {
    Environment = "production"
    Project     = "eks-cluster"
    ManagedBy   = "terraform"
  }
}
```

## 2. GitOps com ArgoCD

### Instalação do ArgoCD

```yaml
# argocd/install.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: argocd
---
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: argocd
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://argoproj.github.io/argo-helm
    chart: argo-cd
    targetRevision: 5.46.7
    helm:
      values: |
        server:
          ingress:
            enabled: true
            hosts:
              - argocd.company.com
            tls:
              - secretName: argocd-tls
                hosts:
                  - argocd.company.com
        configs:
          repositories:
            - url: https://github.com/company/k8s-manifests
              type: git
              sshPrivateKeySecret:
                name: repo-secret
                key: sshPrivateKey
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

### App of Apps Pattern

```yaml
# applications/root-app.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: root-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/company/k8s-manifests
    targetRevision: HEAD
    path: applications
  destination:
    server: https://kubernetes.default.svc
    namespace: argocd
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
```

### Application Definitions

```yaml
# applications/microservice-a.yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: microservice-a
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/company/k8s-manifests
    targetRevision: HEAD
    path: apps/microservice-a/overlays/production
  destination:
    server: https://kubernetes.default.svc
    namespace: microservice-a
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
    syncOptions:
      - CreateNamespace=true
    retry:
      limit: 5
      backoff:
        duration: 5s
        factor: 2
        maxDuration: 3m
```

## 3. Fluxo CI/CD Ideal com GitOps

### Estrutura de Repositórios

```
Repositories Structure:
├── app-repo/                    # Application source code
│   ├── src/
│   ├── Dockerfile
│   └── .github/workflows/
│       └── build-and-push.yml
│
├── k8s-manifests/              # Kubernetes manifests
│   ├── apps/
│   │   └── microservice-a/
│   │       ├── base/
│   │       └── overlays/
│   │           ├── staging/
│   │           └── production/
│   └── infrastructure/
│       ├── argocd/
│       ├── monitoring/
│       └── ingress/
│
└── terraform/                  # Infrastructure as Code
    ├── environments/
    │   ├── staging/
    │   └── production/
    └── modules/
```

### Pipeline de Aplicação

```yaml
# app-repo/.github/workflows/build-and-push.yml
name: Build and Deploy
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Tests
        run: |
          make test
          make security-scan
  
  build:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    outputs:
      image-tag: ${{ steps.meta.outputs.tags }}
    steps:
      - uses: actions/checkout@v3
      
      - name: Docker meta
        id: meta
        uses: docker/metadata-action@v4
        with:
          images: myregistry/myapp
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
      
      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Update Manifest
        uses: fjogeleit/yaml-update-action@main
        with:
          valueFile: 'apps/microservice-a/overlays/production/kustomization.yaml'
          propertyPath: 'images[0].newTag'
          value: ${{ needs.build.outputs.image-tag }}
          repository: company/k8s-manifests
          token: ${{ secrets.REPO_TOKEN }}
```

### Kustomize Structure

```yaml
# apps/microservice-a/base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - deployment.yaml
  - service.yaml
  - configmap.yaml
  - secret.yaml

commonLabels:
  app: microservice-a
  version: v1

images:
  - name: myregistry/microservice-a
    newTag: latest
```

```yaml
# apps/microservice-a/overlays/production/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization

resources:
  - ../../base

patchesStrategicMerge:
  - deployment-patch.yaml

replicas:
  - name: microservice-a
    count: 3

images:
  - name: myregistry/microservice-a
    newTag: main-abc123
```

## 4. Rotação de Segredos com Terraform e GitHub Actions

### External Secrets Operator

```yaml
# infrastructure/external-secrets/secretstore.yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: aws-secretsmanager
  namespace: default
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-east-1
      auth:
        jwt:
          serviceAccountRef:
            name: external-secrets-sa
```

### External Secrets

```yaml
# apps/microservice-a/base/external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: database-credentials
spec:
  refreshInterval: 5m
  secretStoreRef:
    name: aws-secretsmanager
    kind: SecretStore
  target:
    name: database-secret
    creationPolicy: Owner
  data:
    - secretKey: username
      remoteRef:
        key: microservice-a/database
        property: username
    - secretKey: password
      remoteRef:
        key: microservice-a/database
        property: password
```

### Terraform Secret Management

```hcl
# terraform/modules/secrets/main.tf
resource "aws_secretsmanager_secret" "database_credentials" {
  name                    = "${var.app_name}/database"
  description             = "Database credentials for ${var.app_name}"
  recovery_window_in_days = 7

  tags = var.tags
}

resource "aws_secretsmanager_secret_version" "database_credentials" {
  secret_id = aws_secretsmanager_secret.database_credentials.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db_password.result
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

resource "random_password" "db_password" {
  length  = 32
  special = true
}

# Automatic rotation
resource "aws_secretsmanager_secret_rotation" "database_credentials" {
  secret_id           = aws_secretsmanager_secret.database_credentials.id
  rotation_interval   = 30
  
  rotation_rules {
    automatically_after_days = 30
  }
}
```

### GitHub Actions Secret Rotation

```yaml
# .github/workflows/secret-rotation.yml
name: Secret Rotation
on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly on Sunday at 2 AM
  workflow_dispatch:

jobs:
  rotate-secrets:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: us-east-1
      
      - name: Rotate Database Secret
        run: |
          # Generate new password
          NEW_PASSWORD=$(openssl rand -base64 32)
          
          # Update RDS password
          aws rds modify-db-instance \
            --db-instance-identifier myapp-db \
            --master-user-password "$NEW_PASSWORD" \
            --apply-immediately
          
          # Update Secrets Manager
          aws secretsmanager update-secret \
            --secret-id "microservice-a/database" \
            --secret-string "{\"username\":\"admin\",\"password\":\"$NEW_PASSWORD\"}"
      
      - name: Restart Pods
        run: |
          # Restart deployments to pick up new secrets
          kubectl rollout restart deployment/microservice-a -n default
          kubectl rollout status deployment/microservice-a -n default
```

### Vault Integration (Alternative)

```hcl
# terraform/modules/vault-auth/main.tf
resource "vault_auth_backend" "kubernetes" {
  type = "kubernetes"
  path = "kubernetes"
}

resource "vault_kubernetes_auth_backend_config" "kubernetes" {
  backend         = vault_auth_backend.kubernetes.path
  kubernetes_host = var.kubernetes_host
  kubernetes_ca_cert = base64decode(var.kubernetes_ca_cert)
}

resource "vault_kubernetes_auth_backend_role" "microservice_a" {
  backend                          = vault_auth_backend.kubernetes.path
  role_name                        = "microservice-a"
  bound_service_account_names      = ["microservice-a"]
  bound_service_account_namespaces = ["default"]
  token_ttl                        = 3600
  token_policies                   = ["microservice-a-policy"]
}

resource "vault_policy" "microservice_a" {
  name = "microservice-a-policy"

  policy = <<EOT
path "secret/data/microservice-a/*" {
  capabilities = ["read"]
}
EOT
}
```

## Backend e State Locking

### S3 Backend com DynamoDB Lock

```hcl
# terraform/backend.tf
terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
  
  backend "s3" {
    bucket         = "myorg-terraform-state"
    key            = "infrastructure/eks-cluster/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
    
    # Workspace-specific state files
    workspace_key_prefix = "workspaces"
  }
}

# State bucket and lock table
resource "aws_s3_bucket" "terraform_state" {
  bucket = "myorg-terraform-state"
  
  tags = {
    Name        = "Terraform State"
    Environment = "shared"
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_dynamodb_table" "terraform_state_lock" {
  name           = "terraform-state-lock"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name = "Terraform State Lock"
  }
}
```

## Resumo Executivo

### ✅ Implementações Concluídas

1. **Módulo EKS Terraform**
   - Cluster com autoscaling
   - IAM roles para ServiceAccounts
   - Security groups e VPC integration
   - Addons essenciais

2. **GitOps com ArgoCD** 
   - App of Apps pattern
   - Automated sync e self-healing
   - Multi-environment support

3. **CI/CD Pipeline**
   - Build, test, e deploy automatizado
   - Image tagging estratégico
   - Kustomize para customização

4. **Secret Management**
   - AWS Secrets Manager integration
   - External Secrets Operator
   - Rotação automática
   - Vault como alternativa

### 🔄 Próximas Etapas
- Implementação dos manifestos Kubernetes (Seção 3)
- Funções serverless (Seção 3)
- Aplicações Python/Go (Seção 4)
