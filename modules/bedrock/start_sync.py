#!/usr/bin/env python3
import boto3
import sys
import time

def start_sync(kb_id, data_source_id=None):
    """Start a sync job for the Bedrock Knowledge Base."""
    
    region = 'eu-west-1'
    bedrock_agent = boto3.client('bedrock-agent', region_name=region)
    
    try:
        # If data source ID not provided, get the first one
        if not data_source_id:
            print(f"Getting data sources for KB: {kb_id}")
            data_sources = bedrock_agent.list_data_sources(knowledgeBaseId=kb_id)
            
            if not data_sources['dataSourceSummaries']:
                print("Error: No data sources found for this knowledge base!")
                return 1
                
            data_source_id = data_sources['dataSourceSummaries'][0]['dataSourceId']
            print(f"Using data source: {data_source_id}")
        
        # Start ingestion job
        print("\nStarting ingestion job...")
        response = bedrock_agent.start_ingestion_job(
            knowledgeBaseId=kb_id,
            dataSourceId=data_source_id
        )
        
        job_id = response['ingestionJob']['ingestionJobId']
        print(f"Ingestion job started: {job_id}")
        
        # Monitor job status
        print("\nMonitoring job status...")
        while True:
            job_status = bedrock_agent.get_ingestion_job(
                knowledgeBaseId=kb_id,
                dataSourceId=data_source_id,
                ingestionJobId=job_id
            )['ingestionJob']
            
            status = job_status['status']
            print(f"Status: {status}")
            
            if 'statistics' in job_status:
                stats = job_status['statistics']
                print(f"  Documents scanned: {stats.get('numberOfDocumentsScanned', 0)}")
                print(f"  Documents indexed: {stats.get('numberOfDocumentsIndexed', 0)}")
                print(f"  Documents failed: {stats.get('numberOfDocumentsFailed', 0)}")
            
            if status in ['COMPLETE', 'FAILED']:
                break
                
            time.sleep(5)
        
        if status == 'COMPLETE':
            print("\nIngestion completed successfully!")
        else:
            print(f"\nIngestion failed with status: {status}")
            if 'failureReasons' in job_status:
                print(f"Failure reasons: {job_status['failureReasons']}")
            return 1
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python start_sync.py <knowledge_base_id> [data_source_id]")
        sys.exit(1)
        
    kb_id = sys.argv[1]
    data_source_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    exit(start_sync(kb_id, data_source_id))