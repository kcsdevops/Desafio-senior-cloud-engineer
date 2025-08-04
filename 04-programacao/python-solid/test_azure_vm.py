# Test VM Deploy - Azure Cheapest VM
# Script para testar deploy de VM mais barata no Azure usando nosso sistema

import os
import sys
import json
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.factories.provider_factory import create_cloud_provider
from src.config.config_loader import ConfigLoader

def deploy_test_vm():
    """Deploy a cheap test VM in Azure."""
    print("🚀 Iniciando deploy de VM de teste no Azure...")
    print(f"📅 Data/Hora: {datetime.now().isoformat()}")
    
    try:
        # Load configuration
        config_loader = ConfigLoader()
        config_file_path = os.path.join(os.path.dirname(__file__), 'config', 'providers.yaml')
        config = config_loader.load_from_file(config_file_path)
        
        print(f"✅ Configuração carregada com sucesso")
        
        # Create Azure provider
        azure_config = config.get('providers', {}).get('azure', {})
        if not azure_config:
            raise Exception("Configuração Azure não encontrada")
        
        # Override with cheapest settings for testing
        azure_config.update({
            'region': 'East US',  # Região mais barata
            'instance_defaults': {
                'resource_group': 'rg-test-vm',
                'vm_size': 'Standard_B1s',  # VM mais barata (1 vCPU, 1GB RAM)
                'image': {
                    'publisher': 'Canonical',
                    'offer': '0001-com-ubuntu-server-focal',
                    'sku': '20_04-lts-gen2',
                    'version': 'latest'
                }
            },
            'subscription_id': '7a6dcb36-b062-4f1f-822c-43732b1f5707'
        })
        
        print(f"🔧 Configuração Azure ajustada para VM econômica:")
        print(f"   - Região: {azure_config['region']}")
        print(f"   - VM Size: {azure_config['instance_defaults']['vm_size']}")
        print(f"   - Resource Group: {azure_config['instance_defaults']['resource_group']}")
        
        # Create provider
        azure_provider = create_cloud_provider('azure', azure_config)
        print(f"✅ Provider Azure criado com sucesso")
        
        # Test VM specifications
        vm_name = f"test-vm-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        vm_size = "Standard_B1s"  # Cheapest VM: 1 vCPU, 1GB RAM, ~$7.30/month
        
        print(f"\n🔨 Criando VM de teste:")
        print(f"   - Nome: {vm_name}")
        print(f"   - Tamanho: {vm_size}")
        print(f"   - Custo estimado: ~$7.30/mês")
        
        # Create the test VM
        instance = azure_provider.create_instance(
            name=vm_name,
            instance_type=vm_size,
            resource_group='rg-test-vm',
            admin_username='testuser',
            admin_password='TestPassword123!',
            wait_for_completion=False  # Don't wait to avoid timeout
        )
        
        print(f"\n✅ VM criada com sucesso!")
        print(f"   - ID: {instance.id}")
        print(f"   - Nome: {instance.name}")
        print(f"   - Status: {instance.status.value}")
        print(f"   - Provider: {instance.provider}")
        print(f"   - Região: {instance.region}")
        
        # Test listing instances
        print(f"\n📋 Listando todas as VMs...")
        instances = azure_provider.list_instances()
        
        print(f"✅ Total de VMs encontradas: {len(instances)}")
        for idx, inst in enumerate(instances, 1):
            print(f"   {idx}. {inst.name} ({inst.id}) - Status: {inst.status.value}")
        
        # Get specific instance details
        print(f"\n🔍 Buscando detalhes da VM criada...")
        instance_details = azure_provider.get_instance(instance.id)
        
        if instance_details:
            print(f"✅ Detalhes da VM:")
            print(f"   - ID: {instance_details.id}")
            print(f"   - Nome: {instance_details.name}")
            print(f"   - Tipo: {instance_details.instance_type}")
            print(f"   - Status: {instance_details.status.value}")
            print(f"   - IP Público: {instance_details.public_ip or 'N/A'}")
            print(f"   - IP Privado: {instance_details.private_ip or 'N/A'}")
            
            if instance_details.metadata:
                print(f"   - Metadados:")
                for key, value in instance_details.metadata.items():
                    print(f"     • {key}: {value}")
        
        print(f"\n🎉 Teste concluído com sucesso!")
        print(f"💡 Dica: Não esqueça de deletar a VM depois do teste:")
        print(f"   azure_provider.delete_instance('{instance.id}')")
        
        return instance
        
    except Exception as e:
        print(f"❌ Erro durante o deploy: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def cleanup_test_vm(instance_id):
    """Clean up the test VM."""
    print(f"\n🧹 Iniciando limpeza da VM de teste: {instance_id}")
    
    try:
        # Load configuration
        config_loader = ConfigLoader()
        config_file_path = os.path.join(os.path.dirname(__file__), 'config', 'providers.yaml')
        config = config_loader.load_from_file(config_file_path)
        
        # Create Azure provider
        azure_config = config.get('providers', {}).get('azure', {})
        azure_config.update({
            'region': 'East US',
            'subscription_id': '7a6dcb36-b062-4f1f-822c-43732b1f5707'
        })
        
        azure_provider = create_cloud_provider('azure', azure_config)
        
        # Delete the instance
        result = azure_provider.delete_instance(instance_id)
        
        if result:
            print(f"✅ VM deletada com sucesso!")
        else:
            print(f"⚠️ Falha ao deletar VM ou VM não encontrada")
            
    except Exception as e:
        print(f"❌ Erro durante limpeza: {str(e)}")

if __name__ == "__main__":
    print("="*60)
    print("  TESTE DE DEPLOY - VM MAIS BARATA NO AZURE")
    print("="*60)
    
    # Deploy test VM
    instance = deploy_test_vm()
    
    if instance:
        print(f"\n" + "="*60)
        print("  RESULTADO DO TESTE")
        print("="*60)
        print(f"✅ VM criada: {instance.name}")
        print(f"🆔 ID: {instance.id}")
        print(f"💰 Custo estimado: ~$7.30/mês")
        print(f"🌍 Região: East US")
        
        # Ask if user wants to delete
        while True:
            response = input(f"\n❓ Deseja deletar a VM agora? (s/n): ").lower().strip()
            if response in ['s', 'sim', 'y', 'yes']:
                cleanup_test_vm(instance.id)
                break
            elif response in ['n', 'nao', 'não', 'no']:
                print(f"⚠️ VM mantida. Lembre-se de deletar depois!")
                print(f"💡 Para deletar depois, execute:")
                print(f"   cleanup_test_vm('{instance.id}')")
                break
            else:
                print("Por favor, responda com 's' ou 'n'")
