# AWS Lambda Function - S3 Event Processing

import json
import logging
import boto3
import os
from datetime import datetime
from typing import Dict, Any

# Configure structured logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sns_client = boto3.client('sns')
s3_client = boto3.client('s3')

# Environment variables
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda function triggered by S3 events.
    Processes uploaded files and sends notifications via SNS.
    
    Args:
        event: S3 event data
        context: Lambda runtime context
        
    Returns:
        Response with processing status
    """
    
    # Structured logging with correlation ID
    correlation_id = context.aws_request_id
    logger.info({
        "event": "lambda_invocation_start",
        "correlation_id": correlation_id,
        "function_name": context.function_name,
        "function_version": context.function_version,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    try:
        processed_files = []
        
        # Process each S3 record in the event
        for record in event.get('Records', []):
            if record.get('eventSource') == 'aws:s3':
                result = process_s3_event(record, correlation_id)
                processed_files.append(result)
        
        # Send consolidated notification
        if processed_files:
            send_notification(processed_files, correlation_id)
        
        # Structured success log
        logger.info({
            "event": "lambda_invocation_success",
            "correlation_id": correlation_id,
            "processed_files_count": len(processed_files),
            "files": processed_files,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Successfully processed S3 events',
                'processed_files': len(processed_files),
                'correlation_id': correlation_id
            }),
            'headers': {
                'Content-Type': 'application/json',
                'X-Correlation-ID': correlation_id
            }
        }
        
    except Exception as e:
        # Structured error logging
        logger.error({
            "event": "lambda_invocation_error",
            "correlation_id": correlation_id,
            "error_type": type(e).__name__,
            "error_message": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Re-raise for Lambda error handling
        raise

def process_s3_event(record: Dict[str, Any], correlation_id: str) -> Dict[str, Any]:
    """
    Process individual S3 event record.
    
    Args:
        record: S3 event record
        correlation_id: Request correlation ID
        
    Returns:
        Processing result
    """
    
    try:
        # Extract S3 information
        s3_info = record['s3']
        bucket_name = s3_info['bucket']['name']
        object_key = s3_info['object']['key']
        object_size = s3_info['object']['size']
        event_name = record['eventName']
        
        # Log structured event processing
        logger.info({
            "event": "s3_event_processing",
            "correlation_id": correlation_id,
            "bucket": bucket_name,
            "object_key": object_key,
            "object_size": object_size,
            "event_name": event_name,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Get object metadata
        try:
            response = s3_client.head_object(Bucket=bucket_name, Key=object_key)
            content_type = response.get('ContentType', 'unknown')
            last_modified = response.get('LastModified')
            
        except Exception as e:
            logger.warning({
                "event": "s3_metadata_error",
                "correlation_id": correlation_id,
                "bucket": bucket_name,
                "object_key": object_key,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            })
            content_type = 'unknown'
            last_modified = None
        
        # Process based on file type
        processing_result = {
            "bucket": bucket_name,
            "object_key": object_key,
            "object_size": object_size,
            "content_type": content_type,
            "event_name": event_name,
            "processed_at": datetime.utcnow().isoformat(),
            "status": "success"
        }
        
        # Specific processing logic based on content type
        if content_type.startswith('image/'):
            processing_result["processing_type"] = "image_processing"
            processing_result["actions"] = ["thumbnail_generation", "metadata_extraction"]
            
        elif content_type.startswith('application/json'):
            processing_result["processing_type"] = "json_validation"
            processing_result["actions"] = ["schema_validation", "data_enrichment"]
            
        elif content_type.startswith('text/'):
            processing_result["processing_type"] = "text_analysis"
            processing_result["actions"] = ["content_indexing", "sentiment_analysis"]
            
        else:
            processing_result["processing_type"] = "generic_processing"
            processing_result["actions"] = ["virus_scan", "metadata_extraction"]
        
        logger.info({
            "event": "s3_event_processed",
            "correlation_id": correlation_id,
            "processing_result": processing_result,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        return processing_result
        
    except Exception as e:
        logger.error({
            "event": "s3_event_processing_error",
            "correlation_id": correlation_id,
            "record": record,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
        raise

def send_notification(processed_files: list, correlation_id: str) -> None:
    """
    Send SNS notification with processing results.
    
    Args:
        processed_files: List of processed file results
        correlation_id: Request correlation ID
    """
    
    try:
        # Create notification message
        message = {
            "event_type": "s3_files_processed",
            "correlation_id": correlation_id,
            "timestamp": datetime.utcnow().isoformat(),
            "processed_files_count": len(processed_files),
            "summary": {
                "total_size": sum(f.get('object_size', 0) for f in processed_files),
                "processing_types": list(set(f.get('processing_type') for f in processed_files))
            },
            "files": processed_files
        }
        
        # Send SNS message
        if SNS_TOPIC_ARN:
            response = sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Message=json.dumps(message, indent=2),
                Subject=f"S3 Files Processed - {len(processed_files)} files",
                MessageAttributes={
                    'correlation_id': {
                        'DataType': 'String',
                        'StringValue': correlation_id
                    },
                    'event_type': {
                        'DataType': 'String',
                        'StringValue': 's3_files_processed'
                    }
                }
            )
            
            logger.info({
                "event": "sns_notification_sent",
                "correlation_id": correlation_id,
                "message_id": response['MessageId'],
                "topic_arn": SNS_TOPIC_ARN,
                "timestamp": datetime.utcnow().isoformat()
            })
        else:
            logger.warning({
                "event": "sns_topic_not_configured",
                "correlation_id": correlation_id,
                "timestamp": datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error({
            "event": "sns_notification_error",
            "correlation_id": correlation_id,
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        })
        # Don't re-raise - notification failure shouldn't fail the entire function
