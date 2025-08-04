# Teste Técnico - Senior Cloud Engineer

## Objetivo
Avaliar a capacidade de projetar, automatizar, codificar e escalar ambientes cloud modernos, utilizando práticas avançadas de DevOps, IaC, GitOps e segurança em AWS e Azure.

## Estrutura do Projeto

### 📁 01-arquitetura-cloud/
Documentação e diagramas de arquitetura altamente escalável e resiliente:
- Arquitetura AWS (Lambda, API Gateway, SQS/SNS, DynamoDB)
- Estratégias multi-cloud (AWS/Azure)
- Segurança e disponibilidade (IAM, VPC, AZs)
- Integração RBAC, ABAC, OIDC

### 📁 02-terraform-gitops/
Módulos Terraform e configurações GitOps:
- Módulo EKS/AKS com autoscaling
- IAM roles e ServiceAccounts
- Backend remoto e state locking
- Configurações ArgoCD
- Rotação de segredos com GitHub Actions

### 📁 03-kubernetes-serverless/
Manifesto Kubernetes e funções serverless:
- YAMLs para microserviços (replicas, secrets, configmaps, probes, RBAC)
- Funções AWS Lambda / Azure Functions
- Processamento de eventos (S3/Blob)
- Logs estruturados e notificações

### 📁 04-programacao/
Aplicações em Python e Go seguindo princípios SOLID:
- Interface CloudProvider
- Implementações AWS e Azure
- Factory pattern
- Configuração YAML
- Princípios SOLID e DRY

### 📁 docs/
Documentação técnica e respostas dissertativas:
- Análise de arquiteturas
- Explicações de conceitos (control plane, data plane)
- Fluxos CI/CD
- Justificativas técnicas

## Como Executar

### Pré-requisitos
- Terraform >= 1.0
- kubectl
- Docker
- AWS CLI / Azure CLI
- Python 3.9+ ou Go 1.19+

### Estrutura de Pastas
Cada seção contém:
- `README.md` - Documentação específica
- Código fonte implementado
- Exemplos práticos
- Testes unitários (onde aplicável)

## Pontos de Avaliação

### ✅ Arquitetura e Design
- [x] Escalabilidade e resiliência
- [x] Segurança por design
- [x] Multi-cloud consistency
- [x] Disaster recovery

### ✅ Infraestrutura como Código
- [x] Módulos Terraform reutilizáveis
- [x] State management seguro
- [x] GitOps workflows
- [x] Secret rotation

### ✅ Kubernetes e Serverless
- [x] Manifestos otimizados
- [x] RBAC mínimo necessário
- [x] Health checks
- [x] Event-driven functions

### ✅ Programação
- [x] Princípios SOLID
- [x] Design patterns
- [x] Código limpo e testável
- [x] Abstração de provedores

## Autor
**Candidato:** [Seu Nome]  
**Data:** 02 de Agosto de 2025  
**Posição:** Senior Cloud Engineer  

---
*Este projeto demonstra competências avançadas em arquitetura cloud, automação, programação e melhores práticas DevOps.*
