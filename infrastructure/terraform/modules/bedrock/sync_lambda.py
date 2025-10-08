import json
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
    """
    Lambda function to automatically sync Bedrock Knowledge Base when files are added to S3
    """
    
    bedrock_agent = boto3.client('bedrock-agent')
    
    knowledge_base_id = os.environ['KNOWLEDGE_BASE_ID']
    data_source_id = os.environ['DATA_SOURCE_ID']
    
    try:
        # Log the S3 event
        logger.info(f"S3 event received: {json.dumps(event)}")
        
        # Extract S3 bucket and object key from event
        for record in event.get('Records', []):
            if record.get('eventSource') == 'aws:s3':
                bucket_name = record['s3']['bucket']['name']
                object_key = record['s3']['object']['key']
                event_name = record['eventName']
                
                logger.info(f"Processing {event_name} for {bucket_name}/{object_key}")
                
                # Only process files in knowledge-base/ folder
                if object_key.startswith('knowledge-base/') or object_key.startswith('public/knowledge-base/'):
                    
                    # Start ingestion job for the data source
                    response = bedrock_agent.start_ingestion_job(
                        knowledgeBaseId=knowledge_base_id,
                        dataSourceId=data_source_id,
                        description=f"Auto-sync triggered by {object_key}"
                    )
                    
                    ingestion_job_id = response['ingestionJob']['ingestionJobId']
                    
                    logger.info(f"Started ingestion job {ingestion_job_id} for knowledge base {knowledge_base_id}")
                    
                    return {
                        'statusCode': 200,
                        'body': json.dumps({
                            'message': 'Ingestion job started successfully',
                            'ingestionJobId': ingestion_job_id,
                            'knowledgeBaseId': knowledge_base_id,
                            'dataSourceId': data_source_id,
                            'processedFile': object_key
                        })
                    }
                else:
                    logger.info(f"Skipping file {object_key} - not in knowledge-base folder")
    
    except Exception as e:
        logger.error(f"Error starting ingestion job: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to start ingestion job'
            })
        }
    
    return {
        'statusCode': 200,
        'body': json.dumps({'message': 'No eligible files processed'})
    }