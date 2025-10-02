import json
import boto3
import os
import logging
from typing import Dict, Any
import uuid
from datetime import datetime

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'scribbe-ai-dev-output')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Simplified orchestrator that just generates a text file instead of PowerPoint.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse request
        body = json.loads(event.get('body', '{}'))
        document_key = body.get('document_key', 'test.pdf')
        template_key = body.get('template_key', 'default')
        
        # Generate unique presentation ID
        presentation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Create simple text output
        text_content = f"""
Financial Analysis Presentation
Generated: {timestamp}
Document: {document_key}
Template: {template_key}

SLIDE 1: Title
- Financial Analysis Presentation
- South Plains Financial, Inc.
- Q2 2020 Analysis

SLIDE 2: Executive Summary  
- Total loan portfolio grew $229.9M to $454.8M in Q2 2020
- PPP program contributed $215.3M in new loan originations
- Loan yield decreased to 5.26% including PPP impact
- Over 2,000 PPP loans successfully closed during quarter

SLIDE 3: Loan Portfolio Chart
- Loan Balances by Quarter:
  2Q'19: $180.2M, Yield: 5.82%
  3Q'19: $195.8M, Yield: 5.71%
  4Q'19: $209.7M, Yield: 5.64%
  1Q'20: $224.9M, Yield: 5.76%
  2Q'20: $454.8M, Yield: 5.26%

- 2Q'20 Highlights:
  • Total loan increase of $229.9M vs. 1Q'20
  • Growth from $215.3M PPP loans and $34.7M seasonal agriculture loans
  • Partial offset from $24.4M pay-downs in non-residential consumer and direct energy loans
  • Over 2,000 PPP loans closed
  • 2Q'20 yield of 5.26% (down 50 bps vs. 1Q'20 excluding PPP)

This presentation was generated without using any AI models.
All data is predefined and static.
"""
        
        # Save to S3 as text file
        output_key = f"{presentation_id}/presentation_{timestamp}.txt"
        
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=output_key,
            Body=text_content.encode('utf-8'),
            ContentType='text/plain'
        )
        
        logger.info(f"Generated text presentation: s3://{OUTPUT_BUCKET}/{output_key}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'presentation_id': presentation_id,
                'output_url': f"s3://{OUTPUT_BUCKET}/{output_key}",
                'message': 'Text presentation generated successfully - NO AI MODELS USED',
                'content_preview': text_content[:500] + "..."
            })
        }
        
    except Exception as e:
        logger.error(f"Error in simplified orchestrator: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }