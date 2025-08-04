# Cloud Manager - Main Application
# This module serves as the entry point for the cloud management application
# Demonstrates the usage of SOLID principles and design patterns

import sys
import os
import logging
from typing import Optional

# Add src directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.factories.provider_factory import ProviderFactory
from src.config.config_loader import ConfigLoader
from src.interfaces.cloud_provider import CloudProvider, CloudProviderError
from src.models.instance import Instance, InstanceStatus


def setup_logging(config: dict) -> None:
    """
    Configure application logging based on configuration.
    
    Args:
        config: Application configuration dictionary
    """
    log_config = config.get('app', {}).get('logging', {})
    
    level_mapping = {
        'DEBUG': logging.DEBUG,
        'INFO': logging.INFO,
        'WARNING': logging.WARNING,
        'ERROR': logging.ERROR,
        'CRITICAL': logging.CRITICAL
    }
    
    log_level = level_mapping.get(log_config.get('level', 'INFO'), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    # Configure file logging if enabled
    if log_config.get('enable_file_logging', False):
        log_file = log_config.get('log_file', 'cloud-manager.log')
        
        # Create logs directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(log_level)
        file_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        
        # Add file handler to root logger
        logging.getLogger().addHandler(file_handler)


def demonstrate_single_provider(provider_name: str, config: dict) -> None:
    """
    Demonstrate usage with a single cloud provider.
    
    This function shows how the Factory Pattern and SOLID principles
    allow for easy switching between providers.
    
    Args:
        provider_name: Name of the provider to demonstrate
        config: Application configuration
    """
    logger = logging.getLogger(__name__)
    logger.info(f"=== Demonstrating {provider_name.upper()} Provider ===")
    
    try:
        # Create provider using Factory Pattern
        # This demonstrates Dependency Inversion - we depend on abstraction
        provider: CloudProvider = ProviderFactory.create_provider(provider_name, config['providers'])
        
        logger.info(f"Created {provider.get_provider_name()} provider successfully")
        
        # List existing instances
        logger.info("Listing existing instances...")
        existing_instances = provider.list_instances()
        logger.info(f"Found {len(existing_instances)} existing instances")
        
        for instance in existing_instances:
            logger.info(f"  - {instance.get_display_name()} [{instance.status.value}]")
        
        # Create a new instance
        instance_name = f"demo-instance-{provider_name}"
        instance_type = "small"  # This will be mapped to provider-specific types
        
        logger.info(f"Creating new instance: {instance_name}")
        
        # This demonstrates Liskov Substitution - any CloudProvider implementation works
        new_instance: Instance = provider.create_instance(
            name=instance_name,
            instance_type=instance_type,
            wait_for_running=False  # Don't wait to speed up demo
        )
        
        logger.info(f"Successfully created instance: {new_instance.get_display_name()}")
        logger.info(f"Instance details: {new_instance}")
        
        # Get instance information
        logger.info(f"Retrieving instance information...")
        retrieved_instance = provider.get_instance(new_instance.id)
        
        if retrieved_instance:
            logger.info(f"Retrieved instance: {retrieved_instance.get_display_name()}")
            logger.info(f"Status: {retrieved_instance.status.value}")
            logger.info(f"Endpoint: {retrieved_instance.get_endpoint()}")
        else:
            logger.warning("Could not retrieve instance information")
        
        # Clean up - delete the instance
        logger.info(f"Cleaning up - deleting instance: {new_instance.id}")
        deletion_result = provider.delete_instance(new_instance.id)
        
        if deletion_result:
            logger.info("Instance deletion initiated successfully")
        else:
            logger.warning("Instance deletion may have failed")
        
    except CloudProviderError as e:
        logger.error(f"Cloud provider error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)


def demonstrate_multi_provider(config: dict) -> None:
    """
    Demonstrate multi-cloud capabilities.
    
    This function shows how the same interface can be used
    to manage resources across multiple cloud providers.
    
    Args:
        config: Application configuration
    """
    logger = logging.getLogger(__name__)
    logger.info("=== Demonstrating Multi-Cloud Operations ===")
    
    try:
        # Create multiple providers
        # This demonstrates Open/Closed Principle - extensible design
        providers = ProviderFactory.create_multi_provider(config)
        
        logger.info(f"Created {len(providers)} providers: {list(providers.keys())}")
        
        # Demonstrate operations across multiple providers
        for provider_name, provider in providers.items():
            logger.info(f"\n--- {provider_name.upper()} Operations ---")
            
            try:
                # List instances across all providers
                instances = provider.list_instances()
                logger.info(f"{provider_name}: {len(instances)} instances")
                
                # Show instance summary
                running_count = sum(1 for i in instances if i.is_running)
                stopped_count = sum(1 for i in instances if i.is_stopped)
                transitioning_count = sum(1 for i in instances if i.is_transitioning)
                
                logger.info(f"  Running: {running_count}, Stopped: {stopped_count}, Transitioning: {transitioning_count}")
                
            except CloudProviderError as e:
                logger.error(f"Error with {provider_name}: {e}")
                continue
        
        # Demonstrate provider selection based on criteria
        default_provider = ProviderFactory.create_default_provider(config)
        logger.info(f"Default provider: {default_provider.get_provider_name()}")
        
    except CloudProviderError as e:
        logger.error(f"Multi-provider error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in multi-provider demo: {e}", exc_info=True)


def demonstrate_solid_principles() -> None:
    """
    Demonstrate how SOLID principles are applied in the codebase.
    
    This function serves as documentation of the SOLID principles
    implementation in the cloud manager application.
    """
    logger = logging.getLogger(__name__)
    logger.info("=== SOLID Principles Demonstration ===")
    
    logger.info("""
    1. Single Responsibility Principle (SRP):
       ✅ CloudProvider: Only defines cloud operations interface
       ✅ AWSProvider/AzureProvider: Only implement specific cloud operations
       ✅ ProviderFactory: Only responsible for creating provider instances
       ✅ ConfigLoader: Only handles configuration loading and parsing
       ✅ Instance: Only represents instance data and validation
    
    2. Open/Closed Principle (OCP):
       ✅ System is open for extension (new providers can be added)
       ✅ System is closed for modification (existing code doesn't change)
       ✅ New providers can be registered with ProviderFactory.register_provider()
    
    3. Liskov Substitution Principle (LSP):
       ✅ Any CloudProvider implementation can substitute the interface
       ✅ AWSProvider and AzureProvider are completely interchangeable
       ✅ Client code works with any provider without knowing the implementation
    
    4. Interface Segregation Principle (ISP):
       ✅ CloudProvider interface is focused and minimal
       ✅ No unnecessary methods that implementations don't need
       ✅ Separate interfaces for different responsibilities (if needed)
    
    5. Dependency Inversion Principle (DIP):
       ✅ High-level modules depend on abstractions (CloudProvider interface)
       ✅ Low-level modules implement abstractions (AWSProvider, AzureProvider)
       ✅ Factory pattern injects dependencies through abstraction
    """)


def main() -> None:
    """
    Main application entry point.
    
    This function demonstrates the complete cloud management system
    using SOLID principles and design patterns.
    """
    try:
        # Load configuration
        config_path = os.path.join(os.path.dirname(__file__), 'config', 'providers.yaml')
        config = ConfigLoader.load_from_file(config_path)
        
        # Setup logging
        setup_logging(config)
        
        logger = logging.getLogger(__name__)
        logger.info("=== Cloud Manager Application Started ===")
        
        # Show available providers
        available_providers = ProviderFactory.get_available_providers()
        logger.info(f"Available providers: {available_providers}")
        
        # Demonstrate SOLID principles
        demonstrate_solid_principles()
        
        # Demonstrate single provider usage
        for provider_name in available_providers:
            if ProviderFactory.is_provider_available(provider_name):
                demonstrate_single_provider(provider_name, config)
                print()  # Add spacing between providers
        
        # Demonstrate multi-provider capabilities
        demonstrate_multi_provider(config)
        
        logger.info("=== Cloud Manager Application Completed ===")
        
    except FileNotFoundError as e:
        print(f"Configuration file not found: {e}")
        print("Please ensure config/providers.yaml exists")
        sys.exit(1)
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
