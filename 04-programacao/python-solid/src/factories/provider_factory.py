# Provider Factory
# This module implements the Factory Pattern for creating cloud providers
# Follows Open/Closed Principle (OCP) - open for extension, closed for modification

import logging
from typing import Dict, Any, Type

from ..interfaces.cloud_provider import CloudProvider, CloudProviderError
from ..providers.aws_provider import AWSProvider
from ..providers.azure_provider import AzureProvider


class ProviderFactory:
    """
    Factory class for creating cloud provider instances.
    
    This class implements the Factory Pattern and follows several SOLID principles:
    - Single Responsibility: Only responsible for creating providers
    - Open/Closed: Open for extension (new providers), closed for modification
    - Dependency Inversion: Returns abstract CloudProvider interface
    
    The factory pattern allows for dynamic provider creation based on configuration,
    making the system flexible and extensible.
    """
    
    # Registry of available providers
    # This follows the Open/Closed Principle - new providers can be registered
    # without modifying existing code
    _providers: Dict[str, Type[CloudProvider]] = {
        'aws': AWSProvider,
        'azure': AzureProvider,
    }
    
    # Logger for factory operations
    _logger = logging.getLogger(__name__)
    
    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> CloudProvider:
        """
        Create a cloud provider instance based on type and configuration.
        
        This method follows the Dependency Inversion Principle by returning
        the abstract CloudProvider interface rather than concrete implementations.
        
        Args:
            provider_type: Type of provider to create ('aws', 'azure', etc.)
            config: Configuration dictionary for the provider
            
        Returns:
            CloudProvider: Configured provider instance
            
        Raises:
            CloudProviderError: If provider type is not supported or creation fails
        """
        # Normalize provider type
        provider_type = provider_type.lower().strip()
        
        cls._logger.info(f"Creating provider of type: {provider_type}")
        
        # Validate provider type
        if not provider_type:
            raise CloudProviderError("Provider type cannot be empty")
        
        if provider_type not in cls._providers:
            available_providers = ', '.join(cls._providers.keys())
            raise CloudProviderError(
                f"Unsupported provider type '{provider_type}'. "
                f"Available providers: {available_providers}"
            )
        
        # Validate configuration
        if not config:
            raise CloudProviderError("Configuration cannot be empty")
        
        if not isinstance(config, dict):
            raise CloudProviderError("Configuration must be a dictionary")
        
        try:
            # Get provider class
            provider_class = cls._providers[provider_type]
            
            # Extract provider-specific configuration
            provider_config = config.get(provider_type, {})
            if not provider_config:
                cls._logger.warning(
                    f"No specific configuration found for provider '{provider_type}', "
                    "using global configuration"
                )
                provider_config = config
            
            # Create and return provider instance
            provider = provider_class(provider_config)
            
            cls._logger.info(f"Successfully created {provider_type} provider")
            return provider
            
        except Exception as e:
            cls._logger.error(f"Failed to create {provider_type} provider: {str(e)}")
            
            # If it's already a CloudProviderError, re-raise it
            if isinstance(e, CloudProviderError):
                raise
            
            # Otherwise, wrap in CloudProviderError
            raise CloudProviderError(
                f"Failed to create {provider_type} provider: {str(e)}"
            ) from e
    
    @classmethod
    def create_default_provider(cls, config: Dict[str, Any]) -> CloudProvider:
        """
        Create a provider instance using the default provider from configuration.
        
        This method looks for a provider marked as 'default: true' in the configuration
        and creates an instance of that provider.
        
        Args:
            config: Configuration dictionary containing provider settings
            
        Returns:
            CloudProvider: Configured default provider instance
            
        Raises:
            CloudProviderError: If no default provider is found or creation fails
        """
        cls._logger.info("Creating default provider from configuration")
        
        if not config or 'providers' not in config:
            raise CloudProviderError("No providers configuration found")
        
        providers_config = config['providers']
        
        # Find default provider
        default_provider = None
        for provider_type, provider_config in providers_config.items():
            if provider_config.get('default', False):
                default_provider = provider_type
                break
        
        if not default_provider:
            # If no default is specified, use the first available provider
            available_providers = list(providers_config.keys())
            if available_providers:
                default_provider = available_providers[0]
                cls._logger.warning(
                    f"No default provider specified, using first available: {default_provider}"
                )
            else:
                raise CloudProviderError("No providers configured")
        
        cls._logger.info(f"Using default provider: {default_provider}")
        return cls.create_provider(default_provider, config['providers'])
    
    @classmethod
    def register_provider(cls, provider_type: str, provider_class: Type[CloudProvider]) -> None:
        """
        Register a new provider type with the factory.
        
        This method follows the Open/Closed Principle by allowing extension
        of the factory without modifying existing code. New providers can be
        registered at runtime.
        
        Args:
            provider_type: String identifier for the provider
            provider_class: Provider class that implements CloudProvider interface
            
        Raises:
            CloudProviderError: If provider_type or provider_class is invalid
        """
        # Validate inputs
        if not provider_type or not isinstance(provider_type, str):
            raise CloudProviderError("Provider type must be a non-empty string")
        
        if not provider_class:
            raise CloudProviderError("Provider class cannot be None")
        
        # Check if the class implements CloudProvider interface
        if not issubclass(provider_class, CloudProvider):
            raise CloudProviderError(
                f"Provider class must implement CloudProvider interface. "
                f"Got: {provider_class.__name__}"
            )
        
        provider_type = provider_type.lower().strip()
        
        # Log registration
        if provider_type in cls._providers:
            cls._logger.warning(f"Overriding existing provider: {provider_type}")
        else:
            cls._logger.info(f"Registering new provider: {provider_type}")
        
        # Register the provider
        cls._providers[provider_type] = provider_class
    
    @classmethod
    def get_available_providers(cls) -> list[str]:
        """
        Get list of available provider types.
        
        Returns:
            list[str]: List of available provider type names
        """
        return list(cls._providers.keys())
    
    @classmethod
    def is_provider_available(cls, provider_type: str) -> bool:
        """
        Check if a provider type is available.
        
        Args:
            provider_type: Provider type to check
            
        Returns:
            bool: True if provider is available, False otherwise
        """
        return provider_type.lower().strip() in cls._providers
    
    @classmethod
    def create_multi_provider(cls, config: Dict[str, Any]) -> Dict[str, CloudProvider]:
        """
        Create multiple provider instances from configuration.
        
        This method creates instances of all configured providers, which is useful
        for multi-cloud scenarios where you need to manage resources across
        multiple cloud providers simultaneously.
        
        Args:
            config: Configuration dictionary containing provider settings
            
        Returns:
            Dict[str, CloudProvider]: Dictionary mapping provider names to instances
            
        Raises:
            CloudProviderError: If configuration is invalid or provider creation fails
        """
        cls._logger.info("Creating multiple providers from configuration")
        
        if not config or 'providers' not in config:
            raise CloudProviderError("No providers configuration found")
        
        providers_config = config['providers']
        providers = {}
        errors = []
        
        for provider_type in providers_config.keys():
            try:
                provider = cls.create_provider(provider_type, providers_config)
                providers[provider_type] = provider
                cls._logger.info(f"Successfully created provider: {provider_type}")
            except Exception as e:
                error_msg = f"Failed to create provider '{provider_type}': {str(e)}"
                cls._logger.error(error_msg)
                errors.append(error_msg)
        
        if not providers and errors:
            raise CloudProviderError(
                f"Failed to create any providers. Errors: {'; '.join(errors)}"
            )
        
        if errors:
            cls._logger.warning(
                f"Some providers failed to initialize: {'; '.join(errors)}"
            )
        
        cls._logger.info(f"Created {len(providers)} providers successfully")
        return providers


# Convenience function for single provider creation
def create_cloud_provider(provider_name: str, config: Dict[str, Any]) -> CloudProvider:
    """
    Convenience function to create a single cloud provider instance.
    
    Args:
        provider_name: Name of the cloud provider ('aws', 'azure')
        config: Configuration dictionary for the provider
        
    Returns:
        CloudProvider: Configured provider instance
        
    Raises:
        CloudProviderError: If provider creation fails
    """
    return ProviderFactory.create_provider(provider_name, config)
