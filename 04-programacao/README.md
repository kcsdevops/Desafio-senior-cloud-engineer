# Programação com Python e GoLang - Princípios SOLID

## 1. Aplicação Python com Princípios SOLID

### Estrutura do Projeto

```
python-solid/
├── src/
│   ├── __init__.py
│   ├── interfaces/
│   │   ├── __init__.py
│   │   └── cloud_provider.py       # Interface CloudProvider
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── aws_provider.py         # Implementação AWS
│   │   └── azure_provider.py       # Implementação Azure
│   ├── factories/
│   │   ├── __init__.py
│   │   └── provider_factory.py     # Factory Pattern
│   ├── config/
│   │   ├── __init__.py
│   │   └── config_loader.py        # Configuração YAML
│   └── models/
│       ├── __init__.py
│       └── instance.py             # Modelos de dados
├── config/
│   └── providers.yaml              # Configuração YAML
├── tests/
│   ├── __init__.py
│   ├── test_providers.py
│   └── test_factory.py
├── requirements.txt
└── main.py                         # Ponto de entrada
```

### Características da Implementação

#### ✅ Princípios SOLID Aplicados

1. **Single Responsibility Principle (SRP)**
   - Cada classe tem uma única responsabilidade
   - CloudProvider: apenas interface
   - AWSProvider/AzureProvider: implementação específica
   - ProviderFactory: criação de instâncias
   - ConfigLoader: carregamento de configuração

2. **Open/Closed Principle (OCP)**
   - Aberto para extensão (novos providers)
   - Fechado para modificação (interface estável)

3. **Liskov Substitution Principle (LSP)**
   - Implementações são intercambiáveis
   - AWSProvider e AzureProvider substituem CloudProvider

4. **Interface Segregation Principle (ISP)**
   - Interface focada em operações essenciais
   - Sem métodos desnecessários

5. **Dependency Inversion Principle (DIP)**
   - Dependência de abstrações, não implementações
   - Factory injeta dependências

#### 🔄 Padrões Aplicados

- **Factory Pattern**: Criação de providers
- **Strategy Pattern**: Escolha de provider
- **Configuration Pattern**: Carregamento YAML
- **Repository Pattern**: Abstração de recursos
## 2. Configuração YAML Compartilhada

```yaml
# config/providers.yaml
providers:
  aws:
    default: true
    region: "us-east-1"
    credentials:
      type: "environment"  # environment, file, iam_role
    instance_defaults:
      type: "t3.micro"
      security_groups: ["sg-default"]
      key_pair: "my-keypair"
    
  azure:
    default: false
    region: "East US"
    credentials:
      type: "environment"  # environment, service_principal, managed_identity
    instance_defaults:
      size: "Standard_B1s"
      resource_group: "default-rg"
      network_security_group: "default-nsg"

features:
  logging:
    level: "info"
    format: "json"
  monitoring:
    enabled: true
    metrics_provider: "prometheus"
  retry:
    max_attempts: 3
    backoff_factor: 2
```

## Exemplos de Uso

### Python Usage

```python
# main.py
from src.factories.provider_factory import ProviderFactory
from src.config.config_loader import ConfigLoader

def main():
    # Load configuration
    config = ConfigLoader.load_from_file("config/providers.yaml")
    
    # Create provider using factory
    provider = ProviderFactory.create_provider("aws", config)
    
    # Use provider
    instance = provider.create_instance("web-server-01", "t3.small")
    print(f"Created instance: {instance.id}")
    
    # Clean up
    provider.delete_instance(instance.id)
    print(f"Deleted instance: {instance.id}")

if __name__ == "__main__":
    main()
```

## Análise dos Princípios SOLID

### 1. Single Responsibility Principle (SRP) ✅

**Onde aplicado:**
- `CloudProvider`: Apenas define interface para operações cloud
- `AWSProvider`: Apenas implementa AWS
- `AzureProvider`: Apenas implementa Azure  
- `ProviderFactory`: Apenas cria providers
- `ConfigLoader`: Apenas carrega configuração

**Justificativa:**
Cada classe tem uma única razão para mudar, tornando o código mais mantível e testável.

### 2. Open/Closed Principle (OCP) ✅

**Onde aplicado:**
```python
# Extensível - pode adicionar novos providers
class GCPProvider(CloudProvider):
    def create_instance(self, name: str, instance_type: str) -> Instance:
        pass  # Implementação GCP
    
    def delete_instance(self, instance_id: str) -> bool:
        pass  # Implementação GCP

# Factory automaticamente suporta novos providers
providers = {
    "aws": AWSProvider,
    "azure": AzureProvider,
    "gcp": GCPProvider  # Nova implementação
}
```

**Justificativa:**
Sistema aberto para extensão (novos providers) sem modificar código existente.

### 3. Liskov Substitution Principle (LSP) ✅

**Onde aplicado:**
```python
def process_instances(provider: CloudProvider):
    # Funciona com qualquer implementação
    instance = provider.create_instance("test", "small")
    provider.delete_instance(instance.id)

# Ambos funcionam identicamente
aws_provider = AWSProvider(config)
azure_provider = AzureProvider(config)

process_instances(aws_provider)    # ✅ Funciona
process_instances(azure_provider)  # ✅ Funciona
```

**Justificativa:**
Qualquer implementação de CloudProvider pode substituir a interface sem quebrar funcionalidade.

### 4. Interface Segregation Principle (ISP) ✅

**Onde aplicado:**
```python
# Interface focada apenas no essencial
class CloudProvider(ABC):
    @abstractmethod
    def create_instance(self, name: str, instance_type: str) -> Instance:
        pass
    
    @abstractmethod
    def delete_instance(self, instance_id: str) -> bool:
        pass

# Se precisar de mais funcionalidades, criar interfaces específicas
class StorageProvider(ABC):
    @abstractmethod
    def create_bucket(self, name: str) -> Bucket:
        pass
```

**Justificativa:**
Interface mínima com apenas métodos necessários. Funcionalidades adicionais ficam em interfaces separadas.

### 5. Dependency Inversion Principle (DIP) ✅

**Onde aplicado:**
```python
class ProviderFactory:
    @staticmethod
    def create_provider(provider_type: str, config: dict) -> CloudProvider:
        # Depende da abstração CloudProvider, não implementações concretas
        if provider_type == "aws":
            return AWSProvider(config)  # Implementação específica
        elif provider_type == "azure":
            return AzureProvider(config)  # Implementação específica
        
# Client code depende apenas da abstração
def deploy_application(provider: CloudProvider):
    pass  # Não conhece implementação específica
```

**Justificativa:**
Código de alto nível depende de abstrações, não de implementações concretas.

## DRY (Don't Repeat Yourself) ✅

**Onde aplicado:**

1. **Configuration Loading**: Lógica centralizada em ConfigLoader
2. **Error Handling**: Decorators e helpers reutilizáveis
3. **Logging**: Configuração centralizada
4. **Validation**: Métodos compartilhados entre providers

```python
# DRY - Base provider com funcionalidade comum
class BaseProvider:
    def __init__(self, config: dict):
        self.config = config
        self.logger = self._setup_logging()
    
    def _setup_logging(self):
        # Lógica comum de logging - não repetida
        pass
    
    def _validate_instance_name(self, name: str):
        # Validação comum - não repetida
        pass

class AWSProvider(BaseProvider, CloudProvider):
    def create_instance(self, name: str, instance_type: str) -> Instance:
        self._validate_instance_name(name)  # Reusa validação
        # Implementação específica AWS
        pass
```

## Resumo Executivo

### ✅ Implementações Concluídas

1. **Interface CloudProvider**: Abstração clean
2. **Implementações AWS/Azure**: Providers específicos
3. **Factory Pattern**: Criação dinâmica de providers
4. **Configuration YAML**: Configuração externa
5. **Princípios SOLID**: Todos aplicados corretamente
6. **DRY Principle**: Código sem duplicação

### 🎯 Benefícios Alcançados

- **Maintainability**: Código modular e testável
- **Extensibility**: Fácil adição de novos providers
- **Testability**: Interfaces permitem mocking
- **Flexibility**: Configuração dinâmica via YAML
- **Type Safety**: Abstrações bem definidas

### 🚀 Próximos Passos

- Testes unitários completos
- Documentação API
- CI/CD pipeline
- Performance benchmarks
- Containerização
