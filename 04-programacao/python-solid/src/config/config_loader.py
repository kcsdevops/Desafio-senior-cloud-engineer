# Config Loader Module
# This module handles loading and parsing of YAML configuration files
# Follows Single Responsibility Principle (SRP) - only handles configuration

import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path


class ConfigLoaderError(Exception):
    """Custom exception for configuration loading errors."""
    pass


class ConfigLoader:
    """
    Configuration loader for YAML files.
    
    This class follows the Single Responsibility Principle by focusing
    solely on configuration loading, parsing, and environment-specific
    overrides. It provides a clean interface for accessing configuration
    data throughout the application.
    """
    
    _logger = logging.getLogger(__name__)
    
    @classmethod
    def load_from_file(cls, config_path: str, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from a YAML file.
        
        Args:
            config_path: Path to the YAML configuration file
            environment: Optional environment name for overrides
            
        Returns:
            Dict[str, Any]: Parsed configuration dictionary
            
        Raises:
            ConfigLoaderError: If file cannot be loaded or parsed
        """
        cls._logger.info(f"Loading configuration from: {config_path}")
        
        # Validate file path
        if not config_path:
            raise ConfigLoaderError("Configuration file path cannot be empty")
        
        config_file = Path(config_path)
        if not config_file.exists():
            raise ConfigLoaderError(f"Configuration file not found: {config_path}")
        
        if not config_file.is_file():
            raise ConfigLoaderError(f"Configuration path is not a file: {config_path}")
        
        try:
            # Load YAML file
            with open(config_file, 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            if not config:
                raise ConfigLoaderError("Configuration file is empty or invalid")
            
            if not isinstance(config, dict):
                raise ConfigLoaderError("Configuration must be a dictionary/object")
            
            cls._logger.info(f"Successfully loaded configuration with {len(config)} top-level keys")
            
            # Auto-detect environment if not specified
            if not environment:
                environment = cls._detect_environment()
            
            # Apply environment-specific overrides
            if environment:
                config = cls._apply_environment_overrides(config, environment)
            
            # Expand environment variables
            config = cls._expand_environment_variables(config)
            
            # Validate required sections
            cls._validate_configuration(config)
            
            return config
            
        except yaml.YAMLError as e:
            raise ConfigLoaderError(f"Failed to parse YAML file: {e}") from e
        except IOError as e:
            raise ConfigLoaderError(f"Failed to read configuration file: {e}") from e
        except Exception as e:
            raise ConfigLoaderError(f"Unexpected error loading configuration: {e}") from e
    
    @classmethod
    def load_from_dict(cls, config_dict: Dict[str, Any], environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration from a dictionary.
        
        Args:
            config_dict: Configuration dictionary
            environment: Optional environment name for overrides
            
        Returns:
            Dict[str, Any]: Processed configuration dictionary
        """
        if not config_dict or not isinstance(config_dict, dict):
            raise ConfigLoaderError("Configuration dictionary cannot be empty or invalid")
        
        # Make a deep copy to avoid modifying the original
        import copy
        config = copy.deepcopy(config_dict)
        
        # Auto-detect environment if not specified
        if not environment:
            environment = cls._detect_environment()
        
        # Apply environment-specific overrides
        if environment:
            config = cls._apply_environment_overrides(config, environment)
        
        # Expand environment variables
        config = cls._expand_environment_variables(config)
        
        # Validate required sections
        cls._validate_configuration(config)
        
        return config
    
    @classmethod
    def _detect_environment(cls) -> Optional[str]:
        """
        Auto-detect the current environment from environment variables.
        
        Returns:
            Optional[str]: Environment name if detected
        """
        # Check common environment variable names
        env_vars = ['ENVIRONMENT', 'ENV', 'STAGE', 'DEPLOYMENT_ENV']
        
        for env_var in env_vars:
            env_value = os.getenv(env_var)
            if env_value:
                env_value = env_value.lower()
                cls._logger.info(f"Detected environment '{env_value}' from {env_var}")
                return env_value
        
        # Default to development if not specified
        cls._logger.info("No environment detected, using default")
        return None
    
    @classmethod
    def _apply_environment_overrides(cls, config: Dict[str, Any], environment: str) -> Dict[str, Any]:
        """
        Apply environment-specific configuration overrides.
        
        Args:
            config: Base configuration dictionary
            environment: Environment name
            
        Returns:
            Dict[str, Any]: Configuration with environment overrides applied
        """
        if 'environments' not in config:
            cls._logger.debug("No environment overrides section found")
            return config
        
        environments = config['environments']
        if environment not in environments:
            cls._logger.debug(f"No overrides found for environment: {environment}")
            return config
        
        env_overrides = environments[environment]
        cls._logger.info(f"Applying environment overrides for: {environment}")
        
        # Deep merge the overrides
        merged_config = cls._deep_merge_dicts(config, env_overrides)
        
        # Remove the environments section from the final config
        if 'environments' in merged_config:
            del merged_config['environments']
        
        return merged_config
    
    @classmethod
    def _expand_environment_variables(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Expand environment variables in configuration values.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Dict[str, Any]: Configuration with environment variables expanded
        """
        def expand_value(value):
            if isinstance(value, str):
                # Expand environment variables in format ${VAR_NAME} or $VAR_NAME
                expanded = os.path.expandvars(value)
                if expanded != value:
                    cls._logger.debug(f"Expanded '{value}' to '{expanded}'")
                return expanded
            elif isinstance(value, dict):
                return {k: expand_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [expand_value(item) for item in value]
            else:
                return value
        
        return expand_value(config)
    
    @classmethod
    def _deep_merge_dicts(cls, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two dictionaries, with override taking precedence.
        
        Args:
            base: Base dictionary
            override: Override dictionary
            
        Returns:
            Dict[str, Any]: Merged dictionary
        """
        import copy
        result = copy.deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = cls._deep_merge_dicts(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        
        return result
    
    @classmethod
    def _validate_configuration(cls, config: Dict[str, Any]) -> None:
        """
        Validate that the configuration contains required sections.
        
        Args:
            config: Configuration dictionary to validate
            
        Raises:
            ConfigLoaderError: If required sections are missing
        """
        required_sections = ['providers']
        
        for section in required_sections:
            if section not in config:
                raise ConfigLoaderError(f"Required configuration section missing: {section}")
        
        # Validate providers section
        providers = config['providers']
        if not providers or not isinstance(providers, dict):
            raise ConfigLoaderError("Providers section must be a non-empty dictionary")
        
        # Validate at least one provider is configured
        if not any(providers.values()):
            raise ConfigLoaderError("At least one provider must be configured")
        
        cls._logger.debug("Configuration validation passed")
    
    @classmethod
    def get_provider_config(cls, config: Dict[str, Any], provider_name: str) -> Dict[str, Any]:
        """
        Get configuration for a specific provider.
        
        Args:
            config: Full configuration dictionary
            provider_name: Name of the provider
            
        Returns:
            Dict[str, Any]: Provider-specific configuration
            
        Raises:
            ConfigLoaderError: If provider is not configured
        """
        if 'providers' not in config:
            raise ConfigLoaderError("No providers section in configuration")
        
        providers = config['providers']
        if provider_name not in providers:
            available = ', '.join(providers.keys())
            raise ConfigLoaderError(
                f"Provider '{provider_name}' not found. Available: {available}"
            )
        
        return providers[provider_name]
    
    @classmethod
    def get_app_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get application-specific configuration.
        
        Args:
            config: Full configuration dictionary
            
        Returns:
            Dict[str, Any]: Application configuration with defaults
        """
        app_config = config.get('app', {})
        
        # Apply defaults
        defaults = {
            'logging': {
                'level': 'INFO',
                'format': 'text',
                'enable_file_logging': False
            },
            'monitoring': {
                'enabled': False
            },
            'resilience': {
                'max_retries': 3,
                'retry_backoff_factor': 2,
                'request_timeout': 60
            }
        }
        
        return cls._deep_merge_dicts(defaults, app_config)
