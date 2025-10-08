import json
import boto3
import os
import uuid
from datetime import datetime, timedelta
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

dynamodb = boto3.resource('dynamodb')
audit_table = dynamodb.Table(os.environ['AUDIT_TABLE_NAME'])
approval_table = dynamodb.Table(os.environ['APPROVAL_TABLE_NAME'])

def lambda_handler(event, context):
    """
    Lambda function to log user activities and manage file approvals
    """
    
    try:
        # Parse the event
        event_type = event.get('eventType', 'unknown')
        user_id = event.get('userId', 'anonymous')
        action = event.get('action', 'unknown')
        resource = event.get('resource', '')
        details = event.get('details', {})
        ip_address = event.get('ipAddress', '')
        user_agent = event.get('userAgent', '')
        
        timestamp = datetime.utcnow().isoformat()
        log_id = str(uuid.uuid4())
        
        # Create audit log entry
        audit_entry = {
            'log_id': log_id,
            'timestamp': timestamp,
            'user_id': user_id,
            'action': action,
            'resource': resource,
            'event_type': event_type,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'details': json.dumps(details),
            'expires_at': int((datetime.utcnow() + timedelta(days=730)).timestamp())  # 2 years TTL
        }
        
        # Store audit log
        audit_table.put_item(Item=audit_entry)
        
        # Handle file upload events
        if event_type == 'file_upload':
            file_id = details.get('fileId', str(uuid.uuid4()))
            file_name = details.get('fileName', 'unknown')
            file_size = details.get('fileSize', 0)
            file_type = details.get('fileType', 'unknown')
            s3_key = details.get('s3Key', '')
            
            # Check if file needs approval (basic content scanning)
            needs_approval = check_if_needs_approval(file_name, file_type, details)
            
            # Create file approval entry
            approval_entry = {
                'file_id': file_id,
                'file_name': file_name,
                'file_size': file_size,
                'file_type': file_type,
                's3_key': s3_key,
                'uploaded_by': user_id,
                'uploaded_at': timestamp,
                'status': 'pending_approval' if needs_approval else 'approved',
                'needs_approval': needs_approval,
                'flagged_reasons': get_flagged_reasons(file_name, file_type, details) if needs_approval else [],
                'approved_by': 'auto_approved' if not needs_approval else '',
                'approved_at': timestamp if not needs_approval else ''
            }
            
            approval_table.put_item(Item=approval_entry)
            
            logger.info(f"File {file_name} uploaded by {user_id}, approval status: {approval_entry['status']}")
        
        # Handle approval actions
        elif event_type == 'file_approval':
            file_id = details.get('fileId')
            approval_action = details.get('approvalAction')  # 'approve' or 'reject'
            reason = details.get('reason', '')
            
            if file_id and approval_action:
                approval_table.update_item(
                    Key={'file_id': file_id},
                    UpdateExpression='SET #status = :status, approved_by = :approved_by, approved_at = :approved_at, approval_reason = :reason',
                    ExpressionAttributeNames={'#status': 'status'},
                    ExpressionAttributeValues={
                        ':status': 'approved' if approval_action == 'approve' else 'rejected',
                        ':approved_by': user_id,
                        ':approved_at': timestamp,
                        ':reason': reason
                    }
                )
                
                logger.info(f"File {file_id} {approval_action}d by {user_id}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Audit log created successfully',
                'log_id': log_id,
                'timestamp': timestamp
            })
        }
        
    except Exception as e:
        logger.error(f"Error creating audit log: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to create audit log'
            })
        }

def check_if_needs_approval(file_name, file_type, details):
    """
    Determine if a file needs manual approval based on various criteria
    """
    needs_approval = False
    
    # Check file size (files over 50MB need approval)
    file_size = details.get('fileSize', 0)
    if file_size > 50 * 1024 * 1024:  # 50MB
        needs_approval = True
    
    # Check file type restrictions
    suspicious_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif', '.com']
    if any(file_name.lower().endswith(ext) for ext in suspicious_extensions):
        needs_approval = True
    
    # Check for suspicious keywords in filename
    suspicious_keywords = ['admin', 'password', 'secret', 'confidential', 'private']
    if any(keyword in file_name.lower() for keyword in suspicious_keywords):
        needs_approval = True
    
    return needs_approval

def get_flagged_reasons(file_name, file_type, details):
    """
    Get list of reasons why a file was flagged for approval
    """
    reasons = []
    
    file_size = details.get('fileSize', 0)
    if file_size > 50 * 1024 * 1024:
        reasons.append('Large file size (>50MB)')
    
    suspicious_extensions = ['.exe', '.bat', '.cmd', '.scr', '.pif', '.com']
    if any(file_name.lower().endswith(ext) for ext in suspicious_extensions):
        reasons.append('Potentially dangerous file type')
    
    suspicious_keywords = ['admin', 'password', 'secret', 'confidential', 'private']
    flagged_keywords = [kw for kw in suspicious_keywords if kw in file_name.lower()]
    if flagged_keywords:
        reasons.append(f'Contains suspicious keywords: {", ".join(flagged_keywords)}')
    
    return reasons