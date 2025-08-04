# Azure Provider Implementation
# This module implements the CloudProvider interface for Microsoft Azure
# Follows Single Responsibility Principle (SRP) - handles only Azure operations

import logging
from typing import Optional, Dict, Any
from azure.identity import DefaultAzureCredential, EnvironmentCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError

from ..interfaces.cloud_provider import CloudProvider, CloudProviderError
from ..models.instance import Instance, InstanceStatus


class AzureProvider(CloudProvider):
    """
    Azure implementation of the CloudProvider interface.
    
    This class handles all Azure-specific operations for managing Virtual Machines.
    It follows the Single Responsibility Principle by focusing solely on
    Azure operations and the Liskov Substitution Principle by being completely
    interchangeable with other CloudProvider implementations.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Azure provider with configuration.
        
        Args:
            config: Configuration dictionary containing Azure settings
        """
        self.config = config
        self.region = config.get('region', 'East US')
        self.instance_defaults = config.get('instance_defaults', {})
        
        # Setup logging
        self.logger = self._setup_logger()
        
        # Initialize Azure credentials and clients
        try:
            self.credential = self._get_credentials()
            self.subscription_id = self._get_subscription_id()
            
            self.compute_client = ComputeManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
            
            self.resource_client = ResourceManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
            )
            
            self.logger.info(f"Azure provider initialized for region: {self.region}")
            
        except Exception as e:
            raise CloudProviderError(
                f"Failed to initialize Azure provider: {str(e)}",
                provider="azure"
            ) from e
    
    def create_instance(self, name: str, instance_type: str, **kwargs) -> Instance:
        """
        Create a new Azure Virtual Machine.
        
        Args:
            name: Name for the VM
            instance_type: Azure VM size (e.g., 'Standard_B1s')
            **kwargs: Additional Azure-specific parameters
            
        Returns:
            Instance: Created instance object
        """
        try:
            # Get resource group
            resource_group_name = kwargs.get('resource_group') or \
                                self.instance_defaults.get('resource_group', 'default-rg')
            
            # Ensure resource group exists
            self._ensure_resource_group(resource_group_name)
            
            # Build VM parameters
            vm_params = self._build_vm_params(name, instance_type, resource_group_name, **kwargs)
            
            self.logger.info(f"Creating Azure VM '{name}' with size '{instance_type}'")
            
            # Create the VM (async operation)
            vm_operation = self.compute_client.virtual_machines.begin_create_or_update(
                resource_group_name=resource_group_name,
                vm_name=name,
                parameters=vm_params
            )
            
            # Wait for completion if requested
            if kwargs.get('wait_for_completion', False):
                self.logger.info(f"Waiting for VM {name} creation to complete...")
                vm_result = vm_operation.result()
            else:
                # Get the VM object without waiting
                vm_result = vm_operation._initial_response.json() if hasattr(vm_operation, '_initial_response') else None
            
            # Convert to our Instance model
            instance = self._azure_vm_to_instance(vm_result or {'name': name}, resource_group_name)
            
            self.logger.info(f"Successfully initiated Azure VM creation: {name}")
            return instance
            
        except HttpResponseError as e:
            error_code = getattr(e, 'error_code', 'Unknown')
            error_message = str(e)
            
            self.logger.error(f"Azure HttpResponseError creating VM: {error_message}")
            raise CloudProviderError(
                f"Failed to create Azure VM: {error_message}",
                provider="azure",
                error_code=error_code
            ) from e
        except Exception as e:
            self.logger.error(f"Unexpected error creating VM: {str(e)}")
            raise CloudProviderError(
                f"Unexpected error creating Azure VM: {str(e)}",
                provider="azure"
            ) from e
    
    def delete_instance(self, instance_id: str) -> bool:
        """
        Delete an Azure Virtual Machine.
        
        Args:
            instance_id: VM name (Azure uses name as identifier)
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            # Parse instance ID to get resource group and VM name
            resource_group_name, vm_name = self._parse_instance_id(instance_id)
            
            self.logger.info(f"Deleting Azure VM: {vm_name}")
            
            # Delete the VM (async operation)
            delete_operation = self.compute_client.virtual_machines.begin_delete(
                resource_group_name=resource_group_name,
                vm_name=vm_name
            )
            
            # Check if operation was initiated successfully
            # Note: We don't wait for completion to match AWS behavior
            self.logger.info(f"VM {vm_name} deletion initiated successfully")
            return True
            
        except ResourceNotFoundError:
            self.logger.warning(f"VM {instance_id} not found (already deleted?)")
            return True
        except HttpResponseError as e:
            error_code = getattr(e, 'error_code', 'Unknown')
            error_message = str(e)
            
            self.logger.error(f"Azure HttpResponseError deleting VM: {error_message}")
            raise CloudProviderError(
                f"Failed to delete Azure VM: {error_message}",
                provider="azure",
                error_code=error_code
            ) from e
        except Exception as e:
            self.logger.error(f"Unexpected error deleting VM: {str(e)}")
            raise CloudProviderError(
                f"Unexpected error deleting Azure VM: {str(e)}",
                provider="azure"
            ) from e
    
    def get_instance(self, instance_id: str) -> Optional[Instance]:
        """
        Get information about a specific Azure VM.
        
        Args:
            instance_id: VM identifier (format: resource_group/vm_name)
            
        Returns:
            Optional[Instance]: Instance object if found, None otherwise
        """
        try:
            resource_group_name, vm_name = self._parse_instance_id(instance_id)
            
            vm = self.compute_client.virtual_machines.get(
                resource_group_name=resource_group_name,
                vm_name=vm_name
            )
            
            return self._azure_vm_to_instance(vm, resource_group_name)
            
        except ResourceNotFoundError:
            return None
        except HttpResponseError as e:
            if e.status_code == 404:
                return None
            raise CloudProviderError(
                f"Failed to get Azure VM info: {str(e)}",
                provider="azure"
            ) from e
        except Exception as e:
            raise CloudProviderError(
                f"Unexpected error getting Azure VM: {str(e)}",
                provider="azure"
            ) from e
    
    def list_instances(self) -> list[Instance]:
        """
        List all Azure VMs in the subscription.
        
        Returns:
            list[Instance]: List of all instances
        """
        try:
            instances = []
            
            # List VMs across all resource groups
            for vm in self.compute_client.virtual_machines.list_all():
                # Extract resource group from VM ID
                resource_group_name = self._extract_resource_group_from_id(vm.id)
                instance = self._azure_vm_to_instance(vm, resource_group_name)
                instances.append(instance)
            
            self.logger.info(f"Retrieved {len(instances)} Azure VMs")
            return instances
            
        except HttpResponseError as e:
            error_message = str(e)
            self.logger.error(f"Azure HttpResponseError listing VMs: {error_message}")
            raise CloudProviderError(
                f"Failed to list Azure VMs: {error_message}",
                provider="azure"
            ) from e
        except Exception as e:
            self.logger.error(f"Unexpected error listing VMs: {str(e)}")
            raise CloudProviderError(
                f"Unexpected error listing Azure VMs: {str(e)}",
                provider="azure"
            ) from e
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return "azure"
    
    def _get_credentials(self):
        """Get Azure credentials based on configuration."""
        cred_type = self.config.get('credentials', {}).get('type', 'environment')
        
        if cred_type == 'environment':
            return DefaultAzureCredential()
        elif cred_type == 'service_principal':
            return EnvironmentCredential()
        else:
            return DefaultAzureCredential()
    
    def _get_subscription_id(self) -> str:
        """Get Azure subscription ID from environment or config."""
        import os
        
        subscription_id = os.getenv('AZURE_SUBSCRIPTION_ID') or \
                         self.config.get('subscription_id')
        
        if not subscription_id:
            raise CloudProviderError(
                "Azure subscription ID not found. Set AZURE_SUBSCRIPTION_ID environment variable.",
                provider="azure"
            )
        
        return subscription_id
    
    def _ensure_resource_group(self, resource_group_name: str) -> None:
        """Ensure resource group exists, create if it doesn't."""
        try:
            self.resource_client.resource_groups.get(resource_group_name)
        except ResourceNotFoundError:
            self.logger.info(f"Creating resource group: {resource_group_name}")
            self.resource_client.resource_groups.create_or_update(
                resource_group_name,
                {
                    'location': self.region,
                    'tags': {
                        'CreatedBy': 'CloudManager',
                        'Provider': 'azure'
                    }
                }
            )
    
    def _build_vm_params(self, name: str, instance_type: str, resource_group_name: str, **kwargs) -> Dict[str, Any]:
        """Build VM creation parameters."""
        # VM image configuration
        image_config = kwargs.get('image') or self.instance_defaults.get('image', {})
        
        return {
            'location': self.region,
            'hardware_profile': {
                'vm_size': instance_type
            },
            'storage_profile': {
                'image_reference': {
                    'publisher': image_config.get('publisher', 'Canonical'),
                    'offer': image_config.get('offer', '0001-com-ubuntu-server-focal'),
                    'sku': image_config.get('sku', '20_04-lts-gen2'),
                    'version': image_config.get('version', 'latest')
                }
            },
            'os_profile': {
                'computer_name': name,
                'admin_username': kwargs.get('admin_username', 'azureuser'),
                'admin_password': kwargs.get('admin_password', 'TempPassword123!'),
                'disable_password_authentication': False
            },
            'network_profile': {
                'network_interfaces': [
                    {
                        'id': f'/subscriptions/{self.subscription_id}/resourceGroups/{resource_group_name}/providers/Microsoft.Network/networkInterfaces/{name}-nic'
                    }
                ]
            },
            'tags': {
                'Name': name,
                'CreatedBy': 'CloudManager',
                'Provider': 'azure'
            }
        }
    
    def _azure_vm_to_instance(self, azure_vm: Any, resource_group_name: str) -> Instance:
        """Convert Azure VM to our Instance model."""
        # Handle both dict and VM object
        if isinstance(azure_vm, dict):
            vm_name = azure_vm.get('name', 'unknown')
            vm_size = azure_vm.get('hardware_profile', {}).get('vm_size', 'unknown')
            provisioning_state = azure_vm.get('provisioning_state', 'unknown')
            location = azure_vm.get('location', self.region)
        else:
            vm_name = azure_vm.name
            vm_size = azure_vm.hardware_profile.vm_size if azure_vm.hardware_profile else 'unknown'
            provisioning_state = azure_vm.provisioning_state if hasattr(azure_vm, 'provisioning_state') else 'unknown'
            location = azure_vm.location
        
        # Map Azure state to our status enum
        status_mapping = {
            'Creating': InstanceStatus.STARTING,
            'Running': InstanceStatus.RUNNING,
            'Stopping': InstanceStatus.STOPPING,
            'Stopped': InstanceStatus.STOPPED,
            'Deallocating': InstanceStatus.STOPPING,
            'Deallocated': InstanceStatus.STOPPED,
            'Deleting': InstanceStatus.TERMINATED
        }
        status = status_mapping.get(provisioning_state, InstanceStatus.UNKNOWN)
        
        return Instance(
            id=f"{resource_group_name}/{vm_name}",
            name=vm_name,
            instance_type=vm_size,
            status=status,
            provider="azure",
            region=location,
            public_ip=None,  # Would need additional API call to get
            private_ip=None,  # Would need additional API call to get
            metadata={
                'resource_group': resource_group_name,
                'provisioning_state': provisioning_state,
                'subscription_id': self.subscription_id
            }
        )
    
    def _parse_instance_id(self, instance_id: str) -> tuple[str, str]:
        """Parse instance ID to get resource group and VM name."""
        parts = instance_id.split('/', 1)
        if len(parts) == 2:
            return parts[0], parts[1]
        else:
            # Assume default resource group if not specified
            default_rg = self.instance_defaults.get('resource_group', 'default-rg')
            return default_rg, instance_id
    
    def _extract_resource_group_from_id(self, resource_id: str) -> str:
        """Extract resource group name from Azure resource ID."""
        # Azure resource ID format: /subscriptions/{sub}/resourceGroups/{rg}/providers/...
        parts = resource_id.split('/')
        try:
            rg_index = parts.index('resourceGroups')
            return parts[rg_index + 1]
        except (ValueError, IndexError):
            return 'unknown'
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger for Azure provider."""
        logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        
        return logger
