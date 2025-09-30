#!/usr/bin/env python3
import boto3
import json
import sys

def check_kb_status(kb_id=None):
    """Check the status of the Bedrock Knowledge Base and its data sources."""
    
    # Initialize clients
    region = 'eu-west-1'
    bedrock_agent = boto3.client('bedrock-agent', region_name=region)
    opensearch = boto3.client('opensearchserverless', region_name=region)
    
    try:
        # If KB ID not provided, list all knowledge bases
        if not kb_id:
            print("Listing all knowledge bases...")
            kb_list = bedrock_agent.list_knowledge_bases()
            if not kb_list['knowledgeBaseSummaries']:
                print("No knowledge bases found!")
                return
            
            for kb in kb_list['knowledgeBaseSummaries']:
                print(f"\nKnowledge Base: {kb['name']} (ID: {kb['knowledgeBaseId']})")
                print(f"  Status: {kb['status']}")
                print(f"  Updated: {kb['updatedAt']}")
        else:
            # Get specific KB details
            print(f"\nChecking knowledge base: {kb_id}")
            kb = bedrock_agent.get_knowledge_base(knowledgeBaseId=kb_id)['knowledgeBase']
            
            print(f"\nKnowledge Base Details:")
            print(f"  Name: {kb['name']}")
            print(f"  Status: {kb['status']}")
            print(f"  Role ARN: {kb['roleArn']}")
            print(f"  Updated: {kb['updatedAt']}")
            
            # Check data sources
            print(f"\nData Sources:")
            data_sources = bedrock_agent.list_data_sources(knowledgeBaseId=kb_id)
            
            if not data_sources['dataSourceSummaries']:
                print("  WARNING: No data sources found!")
            else:
                for ds in data_sources['dataSourceSummaries']:
                    ds_details = bedrock_agent.get_data_source(
                        knowledgeBaseId=kb_id,
                        dataSourceId=ds['dataSourceId']
                    )['dataSource']
                    
                    print(f"\n  Data Source: {ds_details['name']}")
                    print(f"    ID: {ds_details['dataSourceId']}")
                    print(f"    Status: {ds_details['status']}")
                    print(f"    Updated: {ds_details['updatedAt']}")
                    
                    if 's3Configuration' in ds_details['dataSourceConfiguration']:
                        s3_config = ds_details['dataSourceConfiguration']['s3Configuration']
                        print(f"    S3 Bucket: {s3_config['bucketArn']}")
                    
                    # Check ingestion jobs
                    try:
                        jobs = bedrock_agent.list_ingestion_jobs(
                            knowledgeBaseId=kb_id,
                            dataSourceId=ds['dataSourceId']
                        )
                        
                        print(f"\n    Ingestion Jobs:")
                        if not jobs['ingestionJobSummaries']:
                            print("      WARNING: No ingestion jobs found! Data may not be synced.")
                        else:
                            for job in jobs['ingestionJobSummaries'][:5]:  # Show last 5 jobs
                                print(f"      Job {job['ingestionJobId']}: {job['status']} (Updated: {job['updatedAt']})")
                                
                                # Get job details for the most recent job
                                if job == jobs['ingestionJobSummaries'][0]:
                                    job_details = bedrock_agent.get_ingestion_job(
                                        knowledgeBaseId=kb_id,
                                        dataSourceId=ds['dataSourceId'],
                                        ingestionJobId=job['ingestionJobId']
                                    )['ingestionJob']
                                    
                                    if 'statistics' in job_details:
                                        stats = job_details['statistics']
                                        print(f"        Documents scanned: {stats.get('numberOfDocumentsScanned', 0)}")
                                        print(f"        Documents indexed: {stats.get('numberOfDocumentsIndexed', 0)}")
                                        print(f"        Documents failed: {stats.get('numberOfDocumentsFailed', 0)}")
                    except Exception as e:
                        print(f"      Error checking ingestion jobs: {str(e)}")
            
            # Check OpenSearch collection
            print(f"\n\nOpenSearch Collection Status:")
            collection_name = 'scribbe-ai-dev-kb'
            try:
                collection = opensearch.batch_get_collection(names=[collection_name])
                if collection['collectionDetails']:
                    coll = collection['collectionDetails'][0]
                    print(f"  Collection: {coll['name']}")
                    print(f"  Status: {coll['status']}")
                    print(f"  Endpoint: {coll.get('collectionEndpoint', 'Not available')}")
                else:
                    print(f"  WARNING: Collection '{collection_name}' not found!")
            except Exception as e:
                print(f"  Error checking collection: {str(e)}")
                
    except Exception as e:
        print(f"\nError: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    kb_id = sys.argv[1] if len(sys.argv) > 1 else None
    exit(check_kb_status(kb_id))