# Cloud Provider Interface
# This module defines the abstract interface for cloud providers
# Follows Interface Segregation Principle (ISP) - focused, minimal interface

from abc import ABC, abstractmethod
from typing import Optional
from ..models.instance import Instance

class CloudProvider(ABC):
    """
    Abstract interface for cloud providers.
    
    This interface defines the contract that all cloud providers must implement.
    It follows the Interface Segregation Principle by providing only essential
    methods, avoiding fat interfaces that force implementations to depend on
    methods they don't use.
    """
    
    @abstractmethod
    def create_instance(self, name: str, instance_type: str, **kwargs) -> Instance:
        """
        Create a new virtual machine instance.
        
        Args:
            name: Human-readable name for the instance
            instance_type: Type/size of the instance (e.g., 't3.micro', 'Standard_B1s')
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Instance: Created instance object with ID and metadata
            
        Raises:
            CloudProviderError: If instance creation fails
        """
        pass
    
    @abstractmethod
    def delete_instance(self, instance_id: str) -> bool:
        """
        Delete an existing virtual machine instance.
        
        Args:
            instance_id: Unique identifier of the instance to delete
            
        Returns:
            bool: True if deletion was successful, False otherwise
            
        Raises:
            CloudProviderError: If instance deletion fails
        """
        pass
    
    @abstractmethod
    def get_instance(self, instance_id: str) -> Optional[Instance]:
        """
        Retrieve information about a specific instance.
        
        Args:
            instance_id: Unique identifier of the instance
            
        Returns:
            Optional[Instance]: Instance object if found, None otherwise
            
        Raises:
            CloudProviderError: If unable to query instance information
        """
        pass
    
    @abstractmethod
    def list_instances(self) -> list[Instance]:
        """
        List all instances in the current region/subscription.
        
        Returns:
            list[Instance]: List of all instances
            
        Raises:
            CloudProviderError: If unable to list instances
        """
        pass
    
    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of the cloud provider.
        
        Returns:
            str: Provider name (e.g., 'aws', 'azure')
        """
        pass

class CloudProviderError(Exception):
    """
    Custom exception for cloud provider operations.
    
    This exception should be raised when cloud provider operations fail.
    It provides a consistent error handling mechanism across all providers.
    """
    
    def __init__(self, message: str, provider: str = None, error_code: str = None):
        self.message = message
        self.provider = provider
        self.error_code = error_code
        super().__init__(self.message)
    
    def __str__(self):
        parts = [self.message]
        if self.provider:
            parts.append(f"Provider: {self.provider}")
        if self.error_code:
            parts.append(f"Error Code: {self.error_code}")
        return " | ".join(parts)
