# Instance Model
# This module defines the data models for cloud instances
# Follows Single Responsibility Principle (SRP) - handles only data representation

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any


class InstanceStatus(Enum):
    """
    Enumeration of possible instance statuses.
    
    This provides a consistent status representation across all cloud providers,
    abstracting away provider-specific status names.
    """
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    TERMINATED = "terminated"
    UNKNOWN = "unknown"


@dataclass
class Instance:
    """
    Data model representing a cloud virtual machine instance.
    
    This class follows the Single Responsibility Principle by focusing solely
    on data representation and validation. It provides a consistent interface
    for instance data across all cloud providers.
    
    Attributes:
        id: Unique identifier for the instance
        name: Human-readable name for the instance
        instance_type: Type/size of the instance (e.g., 't3.micro', 'Standard_B1s')
        status: Current status of the instance
        provider: Cloud provider name (e.g., 'aws', 'azure')
        region: Cloud region where instance is located
        public_ip: Public IP address (if assigned)
        private_ip: Private IP address
        created_at: Timestamp when instance was created
        metadata: Additional provider-specific information
    """
    
    id: str
    name: str
    instance_type: str
    status: InstanceStatus
    provider: str
    region: str
    public_ip: Optional[str] = None
    private_ip: Optional[str] = None
    created_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        """
        Post-initialization validation and processing.
        
        This method ensures data consistency and validates required fields.
        """
        # Validate required fields
        if not self.id:
            raise ValueError("Instance ID cannot be empty")
        if not self.name:
            raise ValueError("Instance name cannot be empty")
        if not self.instance_type:
            raise ValueError("Instance type cannot be empty")
        if not self.provider:
            raise ValueError("Provider cannot be empty")
        if not self.region:
            raise ValueError("Region cannot be empty")
        
        # Ensure metadata is not None
        if self.metadata is None:
            self.metadata = {}
        
        # Validate status is InstanceStatus enum
        if not isinstance(self.status, InstanceStatus):
            raise ValueError(f"Status must be an InstanceStatus enum, got {type(self.status)}")
    
    @property
    def is_running(self) -> bool:
        """Check if instance is in running state."""
        return self.status == InstanceStatus.RUNNING
    
    @property
    def is_stopped(self) -> bool:
        """Check if instance is in stopped state."""
        return self.status == InstanceStatus.STOPPED
    
    @property
    def is_terminated(self) -> bool:
        """Check if instance is terminated."""
        return self.status == InstanceStatus.TERMINATED
    
    @property
    def is_transitioning(self) -> bool:
        """Check if instance is in a transitioning state."""
        return self.status in [InstanceStatus.STARTING, InstanceStatus.STOPPING]
    
    def get_display_name(self) -> str:
        """
        Get a display-friendly name for the instance.
        
        Returns:
            str: Display name in format "name (id)"
        """
        return f"{self.name} ({self.id})"
    
    def get_endpoint(self) -> Optional[str]:
        """
        Get the primary endpoint for connecting to this instance.
        
        Prefers public IP over private IP for external connectivity.
        
        Returns:
            Optional[str]: Primary IP address for connection
        """
        return self.public_ip or self.private_ip
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert instance to dictionary representation.
        
        This method is useful for serialization, logging, and API responses.
        
        Returns:
            Dict[str, Any]: Dictionary representation of the instance
        """
        return {
            'id': self.id,
            'name': self.name,
            'instance_type': self.instance_type,
            'status': self.status.value,
            'provider': self.provider,
            'region': self.region,
            'public_ip': self.public_ip,
            'private_ip': self.private_ip,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'metadata': self.metadata,
            'display_name': self.get_display_name(),
            'endpoint': self.get_endpoint(),
            'is_running': self.is_running,
            'is_stopped': self.is_stopped,
            'is_terminated': self.is_terminated,
            'is_transitioning': self.is_transitioning
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Instance':
        """
        Create Instance from dictionary representation.
        
        This method is useful for deserialization from JSON or other formats.
        
        Args:
            data: Dictionary containing instance data
            
        Returns:
            Instance: New instance object
            
        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Parse created_at if present
        created_at = None
        if data.get('created_at'):
            if isinstance(data['created_at'], str):
                created_at = datetime.fromisoformat(data['created_at'])
            elif isinstance(data['created_at'], datetime):
                created_at = data['created_at']
        
        # Parse status
        status = data.get('status')
        if isinstance(status, str):
            try:
                status = InstanceStatus(status)
            except ValueError:
                status = InstanceStatus.UNKNOWN
        elif not isinstance(status, InstanceStatus):
            status = InstanceStatus.UNKNOWN
        
        return cls(
            id=data['id'],
            name=data['name'],
            instance_type=data['instance_type'],
            status=status,
            provider=data['provider'],
            region=data['region'],
            public_ip=data.get('public_ip'),
            private_ip=data.get('private_ip'),
            created_at=created_at,
            metadata=data.get('metadata', {})
        )
    
    def __str__(self) -> str:
        """String representation of the instance."""
        return f"Instance({self.get_display_name()}, {self.status.value}, {self.provider})"
    
    def __repr__(self) -> str:
        """Detailed string representation for debugging."""
        return (
            f"Instance(id='{self.id}', name='{self.name}', "
            f"type='{self.instance_type}', status={self.status}, "
            f"provider='{self.provider}', region='{self.region}')"
        )
