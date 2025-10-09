import json
import boto3
import os
import uuid
from datetime import datetime
import logging
from typing import Dict, Any, Optional, List
import mimetypes

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
DOCUMENTS_BUCKET = os.environ.get('DOCUMENTS_BUCKET', 'scribbe-ai-dev-documents')
CLIENT_SYSTEM_ID = os.environ.get('CLIENT_SYSTEM_ID', 'scribbe-ai-system')

# Initialize DynamoDB for pre-selected uploads tracking
dynamodb = boto3.resource('dynamodb')
try:
    preselected_table = dynamodb.Table(f'scribbe-ai-{ENVIRONMENT}-preselected-uploads')
except:
    preselected_table = None

def generate_s3_key(user_id: str, filename: str, client_system_id: str = None) -> str:
    """
    Generate structured S3 key following the pattern:
    s3://[client-system-ID]/[user-id]/[timestamp]/[filename]
    """
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')[:-3]  # Include milliseconds
    system_id = client_system_id or CLIENT_SYSTEM_ID
    
    # Sanitize filename to remove special characters
    safe_filename = "".join(c for c in filename if c.isalnum() or c in ('-', '_', '.', ' ')).strip()
    safe_filename = safe_filename.replace(' ', '_')
    
    s3_key = f"{system_id}/{user_id}/{timestamp}/{safe_filename}"
    logger.info(f"Generated S3 key: {s3_key}")
    
    return s3_key

def check_file_exists_with_versioning(bucket: str, user_id: str, filename: str, client_system_id: str = None) -> tuple[bool, Optional[str]]:
    """
    Check if file exists and return versioned key if needed.
    Multiple files of the same client are stored in the same folder without overwriting.
    """
    try:
        system_id = client_system_id or CLIENT_SYSTEM_ID
        prefix = f"{system_id}/{user_id}/"
        
        # List all objects with this prefix
        response = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            MaxKeys=1000
        )
        
        existing_files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                obj_filename = obj['Key'].split('/')[-1]  # Get filename from key
                if obj_filename == filename or obj_filename.startswith(filename.rsplit('.', 1)[0]):
                    existing_files.append(obj['Key'])
        
        if existing_files:
            logger.info(f"Found {len(existing_files)} existing files with similar name")
            # Generate new versioned key
            base_name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            version_number = len(existing_files) + 1
            versioned_filename = f"{base_name}_v{version_number}.{ext}" if ext else f"{base_name}_v{version_number}"
            versioned_key = generate_s3_key(user_id, versioned_filename, client_system_id)
            return True, versioned_key
        else:
            # No existing files, use original filename
            return False, generate_s3_key(user_id, filename, client_system_id)
            
    except Exception as e:
        logger.error(f"Error checking file existence: {str(e)}")
        # Fallback to new key generation
        return False, generate_s3_key(user_id, filename, client_system_id)

def create_s3_tags(user_id: str, filename: str, file_size: int, file_type: str, client_system_id: str = None) -> List[Dict[str, str]]:
    """
    Create S3 object tags for traceability with systemID & uploader details
    """
    system_id = client_system_id or CLIENT_SYSTEM_ID
    upload_timestamp = datetime.utcnow().isoformat()
    
    tags = [
        {'Key': 'SystemID', 'Value': system_id},
        {'Key': 'UploaderUserID', 'Value': user_id},
        {'Key': 'UploadTimestamp', 'Value': upload_timestamp},
        {'Key': 'OriginalFilename', 'Value': filename},
        {'Key': 'FileSize', 'Value': str(file_size)},
        {'Key': 'FileType', 'Value': file_type},
        {'Key': 'Environment', 'Value': ENVIRONMENT},
        {'Key': 'Purpose', 'Value': 'document_upload'},
        {'Key': 'Retention', 'Value': 'long_term'}  # For compliance
    ]
    
    logger.info(f"Created {len(tags)} S3 tags for file: {filename}")
    return tags

def upload_file_with_structure_and_tags(
    file_content: bytes,
    user_id: str,
    filename: str,
    file_size: int,
    content_type: str = None,
    client_system_id: str = None,
    metadata: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    Upload file to S3 with proper structure, versioning, and tags
    """
    try:
        # Determine content type
        if not content_type:
            content_type, _ = mimetypes.guess_type(filename)
            content_type = content_type or 'application/octet-stream'
        
        # Check for existing files and get versioned key
        file_exists, s3_key = check_file_exists_with_versioning(
            DOCUMENTS_BUCKET, user_id, filename, client_system_id
        )
        
        # Create tags for traceability
        tags = create_s3_tags(user_id, filename, file_size, content_type, client_system_id)
        
        # Prepare metadata
        upload_metadata = {
            'uploader-user-id': user_id,
            'original-filename': filename,
            'upload-timestamp': datetime.utcnow().isoformat(),
            'system-id': client_system_id or CLIENT_SYSTEM_ID
        }
        
        if metadata:
            upload_metadata.update(metadata)
        
        # Upload file to S3
        s3.put_object(
            Bucket=DOCUMENTS_BUCKET,
            Key=s3_key,
            Body=file_content,
            ContentType=content_type,
            Metadata=upload_metadata,
            Tagging='&'.join([f"{tag['Key']}={tag['Value']}" for tag in tags])
        )
        
        logger.info(f"Successfully uploaded file to S3: {s3_key}")
        
        # Get file info for response
        file_info = {
            's3_key': s3_key,
            'bucket': DOCUMENTS_BUCKET,
            'original_filename': filename,
            'versioned': file_exists,
            'user_id': user_id,
            'client_system_id': client_system_id or CLIENT_SYSTEM_ID,
            'upload_timestamp': datetime.utcnow().isoformat(),
            'file_size': file_size,
            'content_type': content_type,
            'tags': tags,
            'metadata': upload_metadata
        }
        
        return {
            'success': True,
            'file_info': file_info,
            'message': 'File uploaded successfully with proper structure and tags'
        }
        
    except Exception as e:
        logger.error(f"Error uploading file to S3: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'message': 'Failed to upload file to S3'
        }

def list_user_files(user_id: str, client_system_id: str = None, limit: int = 100) -> Dict[str, Any]:
    """
    List all files for a specific user in structured format
    """
    try:
        system_id = client_system_id or CLIENT_SYSTEM_ID
        prefix = f"{system_id}/{user_id}/"
        
        response = s3.list_objects_v2(
            Bucket=DOCUMENTS_BUCKET,
            Prefix=prefix,
            MaxKeys=limit
        )
        
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                # Get object tags and metadata
                try:
                    tags_response = s3.get_object_tagging(Bucket=DOCUMENTS_BUCKET, Key=obj['Key'])
                    tags = {tag['Key']: tag['Value'] for tag in tags_response['TagSet']}
                    
                    head_response = s3.head_object(Bucket=DOCUMENTS_BUCKET, Key=obj['Key'])
                    metadata = head_response.get('Metadata', {})
                    
                    file_info = {
                        'key': obj['Key'],
                        'filename': obj['Key'].split('/')[-1],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat(),
                        'tags': tags,
                        'metadata': metadata,
                        'content_type': head_response.get('ContentType'),
                        'timestamp_folder': obj['Key'].split('/')[-2]  # Extract timestamp folder
                    }
                    files.append(file_info)
                    
                except Exception as e:
                    logger.warning(f"Error getting tags/metadata for {obj['Key']}: {str(e)}")
                    # Still include file without tags/metadata
                    files.append({
                        'key': obj['Key'],
                        'filename': obj['Key'].split('/')[-1],
                        'size': obj['Size'],
                        'last_modified': obj['LastModified'].isoformat()
                    })
        
        return {
            'success': True,
            'files': files,
            'total_files': len(files),
            'user_id': user_id,
            'client_system_id': system_id
        }
        
    except Exception as e:
        logger.error(f"Error listing user files: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'files': []
        }

def get_file_with_metadata(s3_key: str) -> Dict[str, Any]:
    """
    Get file content along with all metadata and tags
    """
    try:
        # Get object
        response = s3.get_object(Bucket=DOCUMENTS_BUCKET, Key=s3_key)
        
        # Get tags
        tags_response = s3.get_object_tagging(Bucket=DOCUMENTS_BUCKET, Key=s3_key)
        tags = {tag['Key']: tag['Value'] for tag in tags_response['TagSet']}
        
        file_info = {
            'content': response['Body'].read(),
            'content_type': response.get('ContentType'),
            'metadata': response.get('Metadata', {}),
            'tags': tags,
            'last_modified': response['LastModified'].isoformat(),
            'size': response['ContentLength']
        }
        
        return {
            'success': True,
            'file_info': file_info
        }
        
    except Exception as e:
        logger.error(f"Error getting file {s3_key}: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def create_preselected_upload_slot(
    user_id: str, 
    expected_filename: str, 
    max_file_size: int = 50 * 1024 * 1024,  # 50MB default
    allowed_types: List[str] = None,
    expires_in_hours: int = 24,
    client_system_id: str = None
) -> Dict[str, Any]:
    """
    Create a pre-selected upload slot that user can use to upload specific file.
    This creates a pre-authorized upload location in S3.
    """
    try:
        if not preselected_table:
            return {
                'success': False,
                'error': 'Pre-selected uploads not configured'
            }
        
        upload_id = str(uuid.uuid4())
        system_id = client_system_id or CLIENT_SYSTEM_ID
        expires_at = datetime.utcnow().timestamp() + (expires_in_hours * 3600)
        
        # Generate the expected S3 key
        expected_s3_key = generate_s3_key(user_id, expected_filename, client_system_id)
        
        # Store pre-selected upload info in DynamoDB
        preselected_item = {
            'upload_id': upload_id,
            'user_id': user_id,
            'client_system_id': system_id,
            'expected_filename': expected_filename,
            'expected_s3_key': expected_s3_key,
            'max_file_size': max_file_size,
            'allowed_types': allowed_types or ['*'],
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': int(expires_at),
            'used': False
        }
        
        preselected_table.put_item(Item=preselected_item)
        
        # Generate presigned URL for upload
        presigned_url = s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': DOCUMENTS_BUCKET,
                'Key': expected_s3_key,
                'ContentType': 'application/octet-stream'
            },
            ExpiresIn=expires_in_hours * 3600
        )
        
        logger.info(f"Created pre-selected upload slot: {upload_id} for user: {user_id}")
        
        return {
            'success': True,
            'upload_id': upload_id,
            'presigned_url': presigned_url,
            'expected_s3_key': expected_s3_key,
            'max_file_size': max_file_size,
            'allowed_types': allowed_types or ['*'],
            'expires_at': datetime.fromtimestamp(expires_at).isoformat(),
            'instructions': {
                'method': 'PUT',
                'url': presigned_url,
                'headers': {
                    'Content-Type': 'application/octet-stream'
                }
            }
        }
        
    except Exception as e:
        logger.error(f"Error creating pre-selected upload: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def validate_preselected_upload(upload_id: str, actual_filename: str, file_size: int) -> Dict[str, Any]:
    """
    Validate that an uploaded file matches the pre-selected upload requirements
    """
    try:
        if not preselected_table:
            return {
                'success': False,
                'error': 'Pre-selected uploads not configured'
            }
        
        # Get pre-selected upload info
        response = preselected_table.get_item(Key={'upload_id': upload_id})
        
        if 'Item' not in response:
            return {
                'success': False,
                'error': 'Invalid upload ID'
            }
        
        preselected = response['Item']
        
        # Check if already used
        if preselected.get('used', False):
            return {
                'success': False,
                'error': 'Upload slot already used'
            }
        
        # Check if expired
        if datetime.utcnow().timestamp() > preselected['expires_at']:
            return {
                'success': False,
                'error': 'Upload slot expired'
            }
        
        # Validate filename
        expected_filename = preselected['expected_filename']
        if actual_filename != expected_filename:
            # Allow versioned filenames
            base_expected = expected_filename.rsplit('.', 1)[0] if '.' in expected_filename else expected_filename
            base_actual = actual_filename.rsplit('.', 1)[0] if '.' in actual_filename else actual_filename
            
            if not base_actual.startswith(base_expected):
                return {
                    'success': False,
                    'error': f'Filename mismatch. Expected: {expected_filename}, Got: {actual_filename}'
                }
        
        # Validate file size
        if file_size > preselected['max_file_size']:
            return {
                'success': False,
                'error': f'File too large. Max size: {preselected["max_file_size"]} bytes'
            }
        
        # Validate file type if specified
        allowed_types = preselected.get('allowed_types', ['*'])
        if '*' not in allowed_types:
            file_ext = actual_filename.split('.')[-1].lower() if '.' in actual_filename else ''
            if file_ext not in [t.lower().replace('.', '') for t in allowed_types]:
                return {
                    'success': False,
                    'error': f'File type not allowed. Allowed types: {allowed_types}'
                }
        
        # Mark as used
        preselected_table.update_item(
            Key={'upload_id': upload_id},
            UpdateExpression='SET #used = :used, #status = :status, #actual_filename = :filename, #actual_size = :size, #completed_at = :completed',
            ExpressionAttributeNames={
                '#used': 'used',
                '#status': 'status',
                '#actual_filename': 'actual_filename',
                '#actual_size': 'actual_size',
                '#completed_at': 'completed_at'
            },
            ExpressionAttributeValues={
                ':used': True,
                ':status': 'completed',
                ':filename': actual_filename,
                ':size': file_size,
                ':completed': datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Validated pre-selected upload: {upload_id}")
        
        return {
            'success': True,
            'preselected_info': preselected,
            'message': 'Upload validated successfully'
        }
        
    except Exception as e:
        logger.error(f"Error validating pre-selected upload: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def list_preselected_uploads(user_id: str, client_system_id: str = None) -> Dict[str, Any]:
    """
    List all pre-selected upload slots for a user
    """
    try:
        if not preselected_table:
            return {
                'success': False,
                'error': 'Pre-selected uploads not configured'
            }
        
        system_id = client_system_id or CLIENT_SYSTEM_ID
        
        # Query by user_id
        response = preselected_table.scan(
            FilterExpression='user_id = :user_id AND client_system_id = :system_id',
            ExpressionAttributeValues={
                ':user_id': user_id,
                ':system_id': system_id
            }
        )
        
        uploads = response.get('Items', [])
        
        # Sort by created_at
        uploads.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        
        return {
            'success': True,
            'uploads': uploads,
            'total': len(uploads)
        }
        
    except Exception as e:
        logger.error(f"Error listing pre-selected uploads: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'uploads': []
        }

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for S3 file management operations
    """
    try:
        logger.info(f"S3 Manager received event: {json.dumps(event)}")
        
        operation = event.get('operation', 'upload')
        
        if operation == 'upload':
            # Handle file upload
            user_id = event.get('user_id')
            filename = event.get('filename')
            file_content = event.get('file_content')  # base64 encoded
            file_size = event.get('file_size', 0)
            content_type = event.get('content_type')
            client_system_id = event.get('client_system_id')
            metadata = event.get('metadata', {})
            
            if not all([user_id, filename, file_content]):
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameters: user_id, filename, file_content'
                    })
                }
            
            # Decode base64 content
            import base64
            decoded_content = base64.b64decode(file_content)
            
            result = upload_file_with_structure_and_tags(
                decoded_content, user_id, filename, file_size, 
                content_type, client_system_id, metadata
            )
            
            return {
                'statusCode': 200 if result['success'] else 500,
                'body': json.dumps(result)
            }
            
        elif operation == 'list':
            # List user files
            user_id = event.get('user_id')
            client_system_id = event.get('client_system_id')
            limit = event.get('limit', 100)
            
            if not user_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameter: user_id'
                    })
                }
            
            result = list_user_files(user_id, client_system_id, limit)
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
            
        elif operation == 'get':
            # Get specific file
            s3_key = event.get('s3_key')
            
            if not s3_key:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameter: s3_key'
                    })
                }
            
            result = get_file_with_metadata(s3_key)
            
            # Don't return file content in response (too large)
            if result['success']:
                result['file_info'].pop('content', None)
            
            return {
                'statusCode': 200 if result['success'] else 404,
                'body': json.dumps(result)
            }
            
        elif operation == 'create_preselected':
            # Create pre-selected upload slot
            user_id = event.get('user_id')
            expected_filename = event.get('expected_filename')
            max_file_size = event.get('max_file_size', 50 * 1024 * 1024)
            allowed_types = event.get('allowed_types')
            expires_in_hours = event.get('expires_in_hours', 24)
            client_system_id = event.get('client_system_id')
            
            if not all([user_id, expected_filename]):
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameters: user_id, expected_filename'
                    })
                }
            
            result = create_preselected_upload_slot(
                user_id, expected_filename, max_file_size,
                allowed_types, expires_in_hours, client_system_id
            )
            
            return {
                'statusCode': 200 if result['success'] else 500,
                'body': json.dumps(result)
            }
            
        elif operation == 'validate_preselected':
            # Validate pre-selected upload
            upload_id = event.get('upload_id')
            actual_filename = event.get('actual_filename')
            file_size = event.get('file_size', 0)
            
            if not all([upload_id, actual_filename]):
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameters: upload_id, actual_filename'
                    })
                }
            
            result = validate_preselected_upload(upload_id, actual_filename, file_size)
            
            return {
                'statusCode': 200 if result['success'] else 400,
                'body': json.dumps(result)
            }
            
        elif operation == 'list_preselected':
            # List pre-selected uploads
            user_id = event.get('user_id')
            client_system_id = event.get('client_system_id')
            
            if not user_id:
                return {
                    'statusCode': 400,
                    'body': json.dumps({
                        'error': 'Missing required parameter: user_id'
                    })
                }
            
            result = list_preselected_uploads(user_id, client_system_id)
            
            return {
                'statusCode': 200,
                'body': json.dumps(result)
            }
            
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Unsupported operation: {operation}. Supported: upload, list, get, create_preselected, validate_preselected, list_preselected'
                })
            }
            
    except Exception as e:
        logger.error(f"Error in S3 Manager Lambda: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }