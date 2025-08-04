# AWS Provider Implementation
# This module implements the CloudProvider interface for Amazon Web Services
# Follows Single Responsibility Principle (SRP) - handles only AWS operations

import boto3
import logging
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError

from ..interfaces.cloud_provider import CloudProvider, CloudProviderError
from ..models.instance import Instance, InstanceStatus


class AWSProvider(CloudProvider):
    """
    AWS implementation of the CloudProvider interface.
    
    This class handles all AWS-specific operations for managing EC2 instances.
    It follows the Single Responsibility Principle by focusing solely on
    AWS operations and the Liskov Substitution Principle by being completely
    interchangeable with other CloudProvider implementations.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize AWS provider with configuration.
        
        Args:
            config: Configuration dictionary containing AWS settings
        """
        self.config = config
        self.region = config.get('region', 'us-east-1')
        self.instance_defaults = config.get('instance_defaults', {})
        
        # Setup logging
        self.logger = self._setup_logger()
        
        # Initialize AWS clients
        try:
            self.ec2_client = boto3.client('ec2', region_name=self.region)
            self.ec2_resource = boto3.resource('ec2', region_name=self.region)
            self.logger.info(f"AWS provider initialized for region: {self.region}")
        except NoCredentialsError as e:
            raise CloudProviderError(
                "AWS credentials not found. Please configure AWS credentials.",
                provider="aws"
            ) from e
        except Exception as e:
            raise CloudProviderError(
                f"Failed to initialize AWS provider: {str(e)}",
                provider="aws"
            ) from e
    
    def create_instance(self, name: str, instance_type: str, **kwargs) -> Instance:
        """
        Create a new EC2 instance.
        
        Args:
            name: Name tag for the instance
            instance_type: EC2 instance type (e.g., 't3.micro')
            **kwargs: Additional AWS-specific parameters
            
        Returns:
            Instance: Created instance object
        """
        try:
            # Merge default configuration with provided parameters
            create_params = self._build_create_params(name, instance_type, **kwargs)
            
            self.logger.info(f"Creating EC2 instance '{name}' with type '{instance_type}'")
            
            # Create the instance
            response = self.ec2_client.run_instances(**create_params)
            
            if not response.get('Instances'):
                raise CloudProviderError(
                    "No instances returned from AWS API",
                    provider="aws"
                )
            
            # Get the created instance
            aws_instance = response['Instances'][0]
            instance_id = aws_instance['InstanceId']
            
            # Wait for instance to be in running state (optional)
            if kwargs.get('wait_for_running', False):
                self.logger.info(f"Waiting for instance {instance_id} to be running...")
                waiter = self.ec2_client.get_waiter('instance_running')
                waiter.wait(InstanceIds=[instance_id])
            
            # Convert to our Instance model
            instance = self._aws_instance_to_instance(aws_instance)
            
            self.logger.info(f"Successfully created EC2 instance: {instance_id}")
            return instance
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            self.logger.error(f"AWS ClientError creating instance: {error_message}")
            raise CloudProviderError(
                f"Failed to create AWS instance: {error_message}",
                provider="aws",
                error_code=error_code
            ) from e
        except Exception as e:
            self.logger.error(f"Unexpected error creating instance: {str(e)}")
            raise CloudProviderError(
                f"Unexpected error creating AWS instance: {str(e)}",
                provider="aws"
            ) from e
    
    def delete_instance(self, instance_id: str) -> bool:
        """
        Delete an EC2 instance.
        
        Args:
            instance_id: EC2 instance ID
            
        Returns:
            bool: True if deletion was successful
        """
        try:
            self.logger.info(f"Deleting EC2 instance: {instance_id}")
            
            # Terminate the instance
            response = self.ec2_client.terminate_instances(InstanceIds=[instance_id])
            
            # Check if termination was initiated
            terminating_instances = response.get('TerminatingInstances', [])
            if not terminating_instances:
                return False
            
            instance_state = terminating_instances[0].get('CurrentState', {})
            state_name = instance_state.get('Name', '')
            
            self.logger.info(f"Instance {instance_id} termination initiated. State: {state_name}")
            return state_name in ['shutting-down', 'terminated']
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            # Handle case where instance doesn't exist
            if error_code == 'InvalidInstanceID.NotFound':
                self.logger.warning(f"Instance {instance_id} not found (already deleted?)")
                return True
            
            self.logger.error(f"AWS ClientError deleting instance: {error_message}")
            raise CloudProviderError(
                f"Failed to delete AWS instance: {error_message}",
                provider="aws",
                error_code=error_code
            ) from e
        except Exception as e:
            self.logger.error(f"Unexpected error deleting instance: {str(e)}")
            raise CloudProviderError(
                f"Unexpected error deleting AWS instance: {str(e)}",
                provider="aws"
            ) from e
    
    def get_instance(self, instance_id: str) -> Optional[Instance]:
        """
        Get information about a specific EC2 instance.
        
        Args:
            instance_id: EC2 instance ID
            
        Returns:
            Optional[Instance]: Instance object if found, None otherwise
        """
        try:
            response = self.ec2_client.describe_instances(InstanceIds=[instance_id])
            
            reservations = response.get('Reservations', [])
            if not reservations:
                return None
            
            instances = reservations[0].get('Instances', [])
            if not instances:
                return None
            
            aws_instance = instances[0]
            return self._aws_instance_to_instance(aws_instance)
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            
            # Return None if instance not found
            if error_code == 'InvalidInstanceID.NotFound':
                return None
            
            # Re-raise other errors
            raise CloudProviderError(
                f"Failed to get AWS instance info: {str(e)}",
                provider="aws",
                error_code=error_code
            ) from e
        except Exception as e:
            raise CloudProviderError(
                f"Unexpected error getting AWS instance: {str(e)}",
                provider="aws"
            ) from e
    
    def list_instances(self) -> list[Instance]:
        """
        List all EC2 instances in the current region.
        
        Returns:
            list[Instance]: List of all instances
        """
        try:
            response = self.ec2_client.describe_instances()
            
            instances = []
            for reservation in response.get('Reservations', []):
                for aws_instance in reservation.get('Instances', []):
                    instance = self._aws_instance_to_instance(aws_instance)
                    instances.append(instance)
            
            self.logger.info(f"Retrieved {len(instances)} EC2 instances")
            return instances
            
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            error_message = e.response.get('Error', {}).get('Message', str(e))
            
            self.logger.error(f"AWS ClientError listing instances: {error_message}")
            raise CloudProviderError(
                f"Failed to list AWS instances: {error_message}",
                provider="aws",
                error_code=error_code
            ) from e
        except Exception as e:
            self.logger.error(f"Unexpected error listing instances: {str(e)}")
            raise CloudProviderError(
                f"Unexpected error listing AWS instances: {str(e)}",
                provider="aws"
            ) from e
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return "aws"
    
    def _build_create_params(self, name: str, instance_type: str, **kwargs) -> Dict[str, Any]:
        """
        Build parameters for EC2 instance creation.
        
        This method follows the DRY principle by centralizing parameter building logic.
        """
        # Start with defaults from configuration
        params = {
            'ImageId': self.instance_defaults.get('ami_id', 'ami-0c02fb55956c7d316'),  # Amazon Linux 2
            'MinCount': 1,
            'MaxCount': 1,
            'InstanceType': instance_type,
            'TagSpecifications': [
                {
                    'ResourceType': 'instance',
                    'Tags': [
                        {'Key': 'Name', 'Value': name},
                        {'Key': 'CreatedBy', 'Value': 'CloudManager'},
                        {'Key': 'Provider', 'Value': 'aws'}
                    ]
                }
            ]
        }
        
        # Add security groups if specified
        security_groups = kwargs.get('security_groups') or self.instance_defaults.get('security_groups')
        if security_groups:
            params['SecurityGroups'] = security_groups
        
        # Add key pair if specified
        key_name = kwargs.get('key_name') or self.instance_defaults.get('key_pair')
        if key_name:
            params['KeyName'] = key_name
        
        # Add subnet if specified
        subnet_id = kwargs.get('subnet_id') or self.instance_defaults.get('subnet_id')
        if subnet_id:
            params['SubnetId'] = subnet_id
        
        # Add user data if specified
        user_data = kwargs.get('user_data')
        if user_data:
            params['UserData'] = user_data
        
        return params
    
    def _aws_instance_to_instance(self, aws_instance: Dict[str, Any]) -> Instance:
        """
        Convert AWS instance data to our Instance model.
        
        This method follows the DRY principle by centralizing conversion logic.
        """
        # Get instance name from tags
        name = "Unknown"
        for tag in aws_instance.get('Tags', []):
            if tag.get('Key') == 'Name':
                name = tag.get('Value', 'Unknown')
                break
        
        # Map AWS state to our status enum
        aws_state = aws_instance.get('State', {}).get('Name', 'unknown')
        status_mapping = {
            'pending': InstanceStatus.STARTING,
            'running': InstanceStatus.RUNNING,
            'shutting-down': InstanceStatus.STOPPING,
            'terminated': InstanceStatus.TERMINATED,
            'stopping': InstanceStatus.STOPPING,
            'stopped': InstanceStatus.STOPPED
        }
        status = status_mapping.get(aws_state, InstanceStatus.UNKNOWN)
        
        return Instance(
            id=aws_instance['InstanceId'],
            name=name,
            instance_type=aws_instance['InstanceType'],
            status=status,
            provider="aws",
            region=self.region,
            public_ip=aws_instance.get('PublicIpAddress'),
            private_ip=aws_instance.get('PrivateIpAddress'),
            created_at=aws_instance.get('LaunchTime'),
            metadata={
                'availability_zone': aws_instance.get('Placement', {}).get('AvailabilityZone'),
                'vpc_id': aws_instance.get('VpcId'),
                'subnet_id': aws_instance.get('SubnetId'),
                'security_groups': [sg['GroupName'] for sg in aws_instance.get('SecurityGroups', [])],
                'key_name': aws_instance.get('KeyName'),
                'architecture': aws_instance.get('Architecture'),
                'virtualization_type': aws_instance.get('VirtualizationType'),
                'root_device_type': aws_instance.get('RootDeviceType')
            }
        )
    
    def _setup_logger(self) -> logging.Logger:
        """
        Setup logger for AWS provider.
        
        This method follows the DRY principle by centralizing logging configuration.
        """
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
