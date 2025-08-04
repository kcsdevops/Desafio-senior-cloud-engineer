#!/usr/bin/env python3
"""
Script para preparar entrega final do projeto.
Cria arquivo ZIP com código-fonte e documentação.
"""

import os
import zipfile
import datetime
from pathlib import Path

def create_delivery_package():
    """Cria pacote de entrega com código-fonte e documentação."""
    
    # Diretório base do projeto
    project_root = Path(__file__).parent
    
    # Nome do arquivo ZIP com timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"ENTREGA-SENIOR-CLOUD-ENGINEER_{timestamp}.zip"
    zip_path = project_root / zip_filename
    
    # Arquivos e pastas para incluir
    include_patterns = [
        "01-arquitetura-cloud/**",
        "02-terraform-gitops/**", 
        "03-kubernetes-serverless/**",
        "04-programacao/**",
        "docs/**",
        ".github/**",
        "README.md",
        "ENTREGA-FINAL.md",
        ".gitignore"
    ]
    
    # Arquivos para excluir
    exclude_patterns = [
        "**/__pycache__/**",
        "**/*.pyc",
        "**/.venv/**",
        "**/node_modules/**",
        "**/.terraform/**",
        "**/*.tfstate*",
        "**/venv/**",
        "**/.env*"
    ]
    
    print(f"🚀 Criando pacote de entrega: {zip_filename}")
    print("📦 Incluindo arquivos...")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        
        # Função para verificar se arquivo deve ser excluído
        def should_exclude(file_path):
            file_str = str(file_path)
            for pattern in exclude_patterns:
                if any(part.startswith('.') and part != '.gitignore' for part in file_path.parts):
                    if not file_str.endswith('.gitignore'):
                        return True
                if '/__pycache__/' in file_str or file_str.endswith('.pyc'):
                    return True
                if '/.venv/' in file_str or '/venv/' in file_str:
                    return True
                if '/.terraform/' in file_str or file_str.endswith('.tfstate'):
                    return True
            return False
        
        # Adicionar arquivos ao ZIP
        for root, dirs, files in os.walk(project_root):
            # Filtrar diretórios
            dirs[:] = [d for d in dirs if not d.startswith('.') or d == '.github']
            
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(project_root)
                
                # Verificar se deve incluir o arquivo
                if not should_exclude(relative_path):
                    zipf.write(file_path, relative_path)
                    print(f"  ✅ {relative_path}")
    
    # Estatísticas do arquivo
    zip_size_mb = zip_path.stat().st_size / (1024 * 1024)
    
    print(f"\n🎉 Pacote criado com sucesso!")
    print(f"📁 Arquivo: {zip_filename}")
    print(f"📊 Tamanho: {zip_size_mb:.2f} MB")
    print(f"📍 Localização: {zip_path}")
    
    # Criar arquivo README para entrega
    readme_content = f"""# ENTREGA FINAL - SENIOR CLOUD ENGINEER

## Informações da Entrega

**Data:** {datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")}
**Arquivo:** {zip_filename}
**Tamanho:** {zip_size_mb:.2f} MB

## Conteúdo do Pacote

### 📁 Estrutura de Diretórios

```
01-arquitetura-cloud/          # Arquiteturas AWS e Azure
02-terraform-gitops/           # Módulos Terraform + ArgoCD
03-kubernetes-serverless/      # Manifests K8s + Functions
04-programacao/python-solid/   # Sistema SOLID testado
docs/                          # Documentação técnica
.github/                       # CI/CD workflows
README.md                      # Documentação principal
ENTREGA-FINAL.md              # Documento dissertativo
```

### 🎯 Destaques Técnicos

✅ **Arquitetura Multi-Cloud** - AWS e Azure event-driven  
✅ **Terraform Modules** - EKS production-ready  
✅ **GitOps** - ArgoCD workflows  
✅ **Kubernetes** - Security policies implementadas  
✅ **Serverless** - Functions AWS Lambda e Azure  
✅ **Python SOLID** - Sistema validado em produção  
✅ **Deploy Real** - VM Azure testada com sucesso  

### 📋 Como Executar

1. **Extrair o arquivo ZIP**
2. **Ler ENTREGA-FINAL.md** - Documento dissertativo completo
3. **Navegar pelas pastas** - Código-fonte organizado por área
4. **Executar testes** - Sistema Python em 04-programacao/python-solid/

### 🔗 Links Importantes

- **Documento Principal:** ENTREGA-FINAL.md
- **Código Python:** 04-programacao/python-solid/
- **Terraform:** 02-terraform-gitops/modules/
- **Serverless:** 03-kubernetes-serverless/serverless-functions/

### 📞 Contato

Para esclarecimentos sobre a implementação, consultar os READMEs em cada diretório ou o documento ENTREGA-FINAL.md.

---

**Gerado automaticamente em:** {datetime.datetime.now().isoformat()}
"""
    
    readme_path = project_root / "LEIA-ME-ENTREGA.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"\n📝 Arquivo LEIA-ME-ENTREGA.md criado")
    print(f"\n✨ Entrega preparada com sucesso!")
    
    return zip_path

if __name__ == "__main__":
    create_delivery_package()
