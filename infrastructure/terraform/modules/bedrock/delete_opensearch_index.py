import boto3
import requests
from requests_aws4auth import AWS4Auth
import os

def delete_index():
    try:
        # Initialize boto3 clients
        region = os.environ.get('REGION_NAME', 'us-east-1')
        collection_name = os.environ.get('COLLECTION_NAME', 'scribbe-ai-dev-kb')
        service = 'aoss'
        credentials = boto3.Session().get_credentials()
        
        if not credentials.access_key or not credentials.secret_key:
            raise Exception("AWS credentials not found")
        
        awsauth = AWS4Auth(credentials.access_key, credentials.secret_key,
                          region, service, session_token=credentials.token)
        
        # Get collection endpoint
        client = boto3.client('opensearchserverless', region_name=region)
        response = client.batch_get_collection(names=[collection_name])
        
        if not response['collectionDetails']:
            raise Exception("Collection not found")
        
        collection_endpoint = response['collectionDetails'][0]['collectionEndpoint']
        
        # Delete the index
        url = f"{collection_endpoint}/scribbe-vectors-v2"
        headers = {"Content-Type": "application/json"}
        
        response = requests.delete(url, auth=awsauth, headers=headers)
        
        if response.status_code in [200, 404]:
            print("Index deleted successfully or didn't exist")
        else:
            print(f"Failed to delete index: {response.status_code} - {response.text}")
            raise Exception(f"Failed to delete index: {response.text}")
    
    except Exception as e:
        print(f"Error deleting index: {str(e)}")
        raise

if __name__ == "__main__":
    delete_index()