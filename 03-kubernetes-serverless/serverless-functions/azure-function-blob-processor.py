# Azure Function - Blob Storage Event Processing

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
import azure.functions as func
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
SERVICE_BUS_CONNECTION_STRING = os.environ.get('SERVICE_BUS_CONNECTION_STRING')
SERVICE_BUS_TOPIC_NAME = os.environ.get('SERVICE_BUS_TOPIC_NAME', 'blob-processing-events')
STORAGE_CONNECTION_STRING = os.environ.get('AzureWebJobsStorage')

def main(blobtrigger: func.InputStream, context: func.Context) -> None:
    """
    Azure Function triggered by Blob Storage events.
    Processes uploaded blobs and sends notifications via Service Bus.
    
    Args:
        blobtrigger: Blob input stream
        context: Function execution context
    """
    
    # Generate correlation ID
    correlation_id = context.invocation_id
    
    # Structured logging with correlation ID
    logger.info(json.dumps({
        "event": "function_invocation_start",
        "correlation_id": correlation_id,
        "function_name": context.function_name,
        "timestamp": datetime.utcnow().isoformat(),
        "blob_name": blobtrigger.name,
        "blob_length": blobtrigger.length
    }))
    
    try:
        # Process the blob event
        result = process_blob_event(blobtrigger, correlation_id)
        
        # Send notification
        if result:
            send_service_bus_notification(result, correlation_id)
        
        # Structured success log
        logger.info(json.dumps({
            "event": "function_invocation_success",
            "correlation_id": correlation_id,
            "processing_result": result,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
    except Exception as e:
        # Structured error logging
        logger.error(json.dumps({
            "event": "function_invocation_error",
            "correlation_id": correlation_id,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "blob_name": blobtrigger.name,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Re-raise for Azure Functions error handling
        raise

def process_blob_event(blobtrigger: func.InputStream, correlation_id: str) -> Dict[str, Any]:
    """
    Process the blob storage event.
    
    Args:
        blobtrigger: Blob input stream
        correlation_id: Request correlation ID
        
    Returns:
        Processing result
    """
    
    try:
        # Extract blob information
        blob_name = blobtrigger.name
        blob_size = blobtrigger.length
        
        # Parse container and blob name from full path
        # Format: container-name/blob-name
        path_parts = blob_name.split('/', 1)
        container_name = path_parts[0] if len(path_parts) > 1 else 'default'
        blob_key = path_parts[1] if len(path_parts) > 1 else blob_name
        
        # Log structured event processing
        logger.info(json.dumps({
            "event": "blob_event_processing",
            "correlation_id": correlation_id,
            "container": container_name,
            "blob_key": blob_key,
            "blob_size": blob_size,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        # Get blob metadata and properties
        blob_metadata = get_blob_metadata(container_name, blob_key, correlation_id)
        
        # Determine content type
        content_type = blob_metadata.get('content_type', 'unknown')
        
        # Read blob content for processing (first 1KB for analysis)
        blob_content_preview = None
        try:
            blob_data = blobtrigger.read(1024)  # Read first 1KB
            if blob_data:
                blob_content_preview = {
                    "preview_size": len(blob_data),
                    "has_content": True
                }
                
                # Basic content analysis
                if content_type.startswith('text/') or content_type == 'application/json':
                    try:
                        text_preview = blob_data.decode('utf-8')[:500]
                        blob_content_preview["text_preview"] = text_preview
                        blob_content_preview["is_text"] = True
                    except UnicodeDecodeError:
                        blob_content_preview["is_text"] = False
                        
        except Exception as e:
            logger.warning(json.dumps({
                "event": "blob_content_read_error",
                "correlation_id": correlation_id,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }))
        
        # Create processing result
        processing_result = {
            "container": container_name,
            "blob_key": blob_key,
            "blob_size": blob_size,
            "content_type": content_type,
            "metadata": blob_metadata,
            "content_preview": blob_content_preview,
            "processed_at": datetime.utcnow().isoformat(),
            "status": "success"
        }
        
        # Determine processing type based on content type
        if content_type.startswith('image/'):
            processing_result["processing_type"] = "image_processing"
            processing_result["actions"] = ["thumbnail_generation", "metadata_extraction", "virus_scan"]
            
        elif content_type == 'application/json':
            processing_result["processing_type"] = "json_validation"
            processing_result["actions"] = ["schema_validation", "data_enrichment", "indexing"]
            
        elif content_type.startswith('text/'):
            processing_result["processing_type"] = "text_analysis"
            processing_result["actions"] = ["content_indexing", "sentiment_analysis", "keyword_extraction"]
            
        elif content_type.startswith('application/pdf'):
            processing_result["processing_type"] = "document_processing"
            processing_result["actions"] = ["text_extraction", "indexing", "virus_scan"]
            
        else:
            processing_result["processing_type"] = "generic_processing"
            processing_result["actions"] = ["virus_scan", "metadata_extraction", "backup"]
        
        logger.info(json.dumps({
            "event": "blob_event_processed",
            "correlation_id": correlation_id,
            "processing_result": processing_result,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
        return processing_result
        
    except Exception as e:
        logger.error(json.dumps({
            "event": "blob_event_processing_error",
            "correlation_id": correlation_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }))
        raise

def get_blob_metadata(container_name: str, blob_key: str, correlation_id: str) -> Dict[str, Any]:
    """
    Get blob metadata and properties.
    
    Args:
        container_name: Container name
        blob_key: Blob key/name
        correlation_id: Request correlation ID
        
    Returns:
        Blob metadata dictionary
    """
    
    metadata = {}
    
    try:
        if STORAGE_CONNECTION_STRING:
            blob_service_client = BlobServiceClient.from_connection_string(STORAGE_CONNECTION_STRING)
            blob_client = blob_service_client.get_blob_client(
                container=container_name, 
                blob=blob_key
            )
            
            # Get blob properties
            properties = blob_client.get_blob_properties()
            
            metadata = {
                "content_type": properties.content_settings.content_type,
                "content_length": properties.size,
                "etag": properties.etag,
                "last_modified": properties.last_modified.isoformat() if properties.last_modified else None,
                "creation_time": properties.creation_time.isoformat() if properties.creation_time else None,
                "blob_type": str(properties.blob_type),
                "lease_status": str(properties.lease.status) if properties.lease else None,
                "metadata": dict(properties.metadata) if properties.metadata else {}
            }
            
    except ResourceNotFoundError:
        logger.warning(json.dumps({
            "event": "blob_not_found",
            "correlation_id": correlation_id,
            "container": container_name,
            "blob_key": blob_key,
            "timestamp": datetime.utcnow().isoformat()
        }))
        
    except Exception as e:
        logger.warning(json.dumps({
            "event": "blob_metadata_error",
            "correlation_id": correlation_id,
            "container": container_name,
            "blob_key": blob_key,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }))
    
    return metadata

def send_service_bus_notification(processing_result: Dict[str, Any], correlation_id: str) -> None:
    """
    Send Service Bus notification with processing results.
    
    Args:
        processing_result: Processing result data
        correlation_id: Request correlation ID
    """
    
    try:
        if not SERVICE_BUS_CONNECTION_STRING:
            logger.warning(json.dumps({
                "event": "service_bus_not_configured",
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat()
            }))
            return
        
        # Create notification message
        message_body = {
            "event_type": "blob_processed",
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "processing_result": processing_result,
            "source": "azure-function-blob-processor"
        }
        
        # Create Service Bus client and send message
        with ServiceBusClient.from_connection_string(SERVICE_BUS_CONNECTION_STRING) as client:
            with client.get_topic_sender(topic_name=SERVICE_BUS_TOPIC_NAME) as sender:
                
                # Create message with properties
                message = ServiceBusMessage(
                    body=json.dumps(message_body, indent=2),
                    content_type="application/json",
                    correlation_id=correlation_id,
                    message_id=f"blob-processed-{correlation_id}",
                    application_properties={
                        "event_type": "blob_processed",
                        "processing_type": processing_result.get("processing_type", "unknown"),
                        "container": processing_result.get("container", "unknown"),
                        "blob_size": processing_result.get("blob_size", 0)
                    }
                )
                
                # Send message
                sender.send_messages(message)
                
                logger.info(json.dumps({
                    "event": "service_bus_notification_sent",
                    "correlation_id": correlation_id,
                    "topic_name": SERVICE_BUS_TOPIC_NAME,
                    "message_id": message.message_id,
                    "timestamp": datetime.utcnow().isoformat()
                }))
                
    except Exception as e:
        logger.error(json.dumps({
            "event": "service_bus_notification_error",
            "correlation_id": correlation_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }))
        # Don't re-raise - notification failure shouldn't fail the entire function
