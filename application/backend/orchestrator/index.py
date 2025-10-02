import json
import logging
from typing import Dict, Any
import uuid
from datetime import datetime

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Ultra-simplified orchestrator that returns immediately without any AWS calls.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Generate unique presentation ID
        presentation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Return immediately without any processing
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({
                'presentation_id': presentation_id,
                'message': f'Presentation request received at {timestamp}',
                'status': 'success'
            })
        }
        
    except Exception as e:
        logger.error(f"Error in ultra-simplified orchestrator: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }