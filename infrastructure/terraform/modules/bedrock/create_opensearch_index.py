import boto3
import requests
from requests_aws4auth import AWS4Auth
import json
import time
import os

def create_index():
    try:
        # Initialize boto3 clients
        region = os.environ.get('REGION_NAME', 'eu-west-1')
        collection_name = os.environ.get('COLLECTION_NAME', 'scribbe-ai-dev-kb')
        service = 'aoss'
        credentials = boto3.Session().get_credentials()
        
        if not credentials.access_key or not credentials.secret_key:
            raise Exception("AWS credentials not found")
        
        awsauth = AWS4Auth(credentials.access_key, credentials.secret_key,
                          region, service, session_token=credentials.token)
        
        # Get collection endpoint
        client = boto3.client('opensearchserverless', region_name=region)
        
        # Retry logic for collection retrieval
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = client.batch_get_collection(names=[collection_name])
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Failed to get collection after {max_retries} attempts: {str(e)}")
                time.sleep(10)
        
        if not response['collectionDetails']:
            raise Exception("Collection not found")
        
        collection_endpoint = response['collectionDetails'][0]['collectionEndpoint']
        
        # Wait for collection to be active
        status = response['collectionDetails'][0]['status']
        while status != 'ACTIVE':
            print(f"Waiting for collection to be active. Current status: {status}")
            time.sleep(10)
            response = client.batch_get_collection(names=[collection_name])
            status = response['collectionDetails'][0]['status']
        
        # Define index mapping for Bedrock Knowledge Base
        index_body = {
            "settings": {
                "index": {
                    "knn": True,
                    "knn.algo_param.ef_search": 512
                }
            },
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": 1024,
                        "method": {
                            "name": "hnsw",
                            "space_type": "l2",
                            "engine": "faiss",
                            "parameters": {
                                "ef_construction": 512,
                                "m": 16
                            }
                        }
                    },
                    "content": {
                        "type": "text"
                    },
                    "metadata": {
                        "type": "object"
                    }
                }
            }
        }
        
        # Create the index
        url = f"{collection_endpoint}/scribbe-vectors"
        headers = {"Content-Type": "application/json"}
        
        # Check if index already exists and delete it if it has wrong dimensions
        response = requests.head(url, auth=awsauth, headers=headers)
        if response.status_code == 200:
            print("Index already exists, checking dimensions...")
            get_response = requests.get(url, auth=awsauth, headers=headers)
            if get_response.status_code == 200:
                existing_mapping = get_response.json()
                existing_dim = existing_mapping.get('scribbe-vectors', {}).get('mappings', {}).get('properties', {}).get('embedding', {}).get('dimension')
                if existing_dim != 1024:
                    print(f"Existing index has wrong dimension ({existing_dim}), deleting...")
                    delete_response = requests.delete(url, auth=awsauth, headers=headers)
                    if delete_response.status_code != 200:
                        print(f"Failed to delete index: {delete_response.status_code} - {delete_response.text}")
                    else:
                        print("Index deleted successfully")
                        time.sleep(10)  # Wait for deletion to propagate
                else:
                    print("Index has correct dimensions")
                    return
        
        # Create the index
        response = requests.put(url, auth=awsauth, json=index_body, headers=headers)
        
        if response.status_code in [200, 201]:
            print("Index created successfully")
        else:
            print(f"Failed to create index: {response.status_code} - {response.text}")
            raise Exception(f"Failed to create index: {response.text}")
    
    except Exception as e:
        print(f"Error creating index: {str(e)}")
        raise

if __name__ == "__main__":
    create_index()