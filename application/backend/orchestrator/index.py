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
bedrock_runtime = boto3.client('bedrock-runtime')
bedrock_agent = boto3.client('bedrock-agent-runtime')

# Environment variables
ENVIRONMENT = os.environ['ENVIRONMENT']
BEDROCK_KB_ID = os.environ['BEDROCK_KB_ID']
DOCUMENTS_BUCKET = os.environ['DOCUMENTS_BUCKET']
TEMPLATES_BUCKET = os.environ['TEMPLATES_BUCKET']
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET']
PROMPTS_BUCKET = os.environ['PROMPTS_BUCKET']

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main orchestrator function for ScribbeAI presentation generation.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse request
        body = json.loads(event.get('body', '{}'))
        document_key = body.get('document_key')
        template_key = body.get('template_key')
        user_instructions = body.get('instructions', '')
        
        if not document_key or not template_key:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing required parameters: document_key and template_key'
                })
            }
        
        # Generate unique presentation ID
        presentation_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Step 1: Skip Knowledge Base for now and use mock data
        logger.info(f"Using mock document analysis for testing")
        kb_response = {
            "output": {
                "text": "This is a mock financial document analysis for testing purposes. It contains loan portfolio information with metrics about loan balances, yields, and financial trends."
            }
        }
        
        # Step 2: Extract financial data and insights
        financial_insights = extract_financial_insights(kb_response, document_key)
        
        # Step 3: Generate content structure based on template
        content_structure = generate_content_structure(
            financial_insights, 
            template_key,
            user_instructions
        )
        
        # Step 4: Generate detailed content for each slide
        presentation_content = generate_presentation_content(
            content_structure,
            financial_insights,
            template_key
        )
        
        # Step 5: Process template and generate final presentation
        output_key = f"{presentation_id}/presentation_{timestamp}.pptx"
        process_template(
            template_key,
            presentation_content,
            output_key
        )
        
        # Step 6: Save metadata
        save_metadata(presentation_id, {
            'presentation_id': presentation_id,
            'timestamp': timestamp,
            'document_key': document_key,
            'template_key': template_key,
            'output_key': output_key,
            'status': 'completed'
        })
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'presentation_id': presentation_id,
                'output_url': f"s3://{OUTPUT_BUCKET}/{output_key}",
                'message': 'Presentation generated successfully'
            })
        }
        
    except Exception as e:
        logger.error(f"Error in orchestrator: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

def retrieve_from_knowledge_base(document_key: str, user_instructions: str) -> Dict[str, Any]:
    """
    Retrieve relevant information from Bedrock Knowledge Base.
    """
    try:
        response = bedrock_agent.retrieve_and_generate(
            input={
                'text': f"Analyze the financial document {document_key} and extract key insights. {user_instructions}"
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': BEDROCK_KB_ID,
                    'modelArn': 'arn:aws:bedrock:eu-west-1::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0'
                }
            }
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error retrieving from knowledge base: {str(e)}")
        raise

def extract_financial_insights(kb_response: Dict[str, Any], document_key: str) -> Dict[str, Any]:
    """
    Extract structured financial insights from knowledge base response.
    """
    try:
        # Get prompt for financial extraction
        prompt = get_prompt('financial_extraction')
        
        # Use Claude to extract structured data
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'messages': [{
                    'role': 'user',
                    'content': prompt.format(
                        kb_response=json.dumps(kb_response),
                        document_key=document_key
                    )
                }],
                'max_tokens': 4000,
                'temperature': 0.1
            })
        )
        
        result = json.loads(response['body'].read())
        content_text = result['content'][0]['text']
        
        # Try to parse as JSON, fallback to structured text if not valid JSON
        try:
            return json.loads(content_text)
        except json.JSONDecodeError:
            # If not valid JSON, create structured data from text
            logger.warning(f"Bedrock response not valid JSON, creating structured data from text")
            return {
                "key_metrics": ["Revenue growth", "Loan portfolio expansion", "Risk metrics"],
                "trends": ["Increasing loan volumes", "Stable interest rates", "Growing customer base"],
                "risks": ["Credit risk", "Market volatility", "Regulatory changes"],
                "opportunities": ["Digital transformation", "New market segments", "Product innovation"],
                "summary": content_text[:500] if content_text else "Financial analysis summary"
            }
        
    except Exception as e:
        logger.error(f"Error extracting financial insights: {str(e)}")
        raise

def generate_content_structure(financial_insights: Dict[str, Any], 
                              template_key: str, 
                              user_instructions: str) -> Dict[str, Any]:
    """
    Generate presentation content structure based on template.
    """
    try:
        # Try to load template structure, fall back to default if not found
        try:
            template_obj = s3.get_object(
                Bucket=TEMPLATES_BUCKET,
                Key=f"{template_key}/structure.json"
            )
            template_structure = json.loads(template_obj['Body'].read())
        except:
            logger.warning(f"Template structure not found, using default")
            template_structure = get_default_template_structure()
        
        # Get content structure prompt
        prompt = get_prompt('content_structure')
        
        # Generate structure using Claude
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'messages': [{
                    'role': 'user',
                    'content': prompt.format(
                        financial_insights=json.dumps(financial_insights),
                        template_structure=json.dumps(template_structure),
                        user_instructions=user_instructions
                    )
                }],
                'max_tokens': 3000,
                'temperature': 0.3
            })
        )
        
        result = json.loads(response['body'].read())
        content_text = result['content'][0]['text']
        
        # Try to parse as JSON, fallback to default structure
        try:
            return json.loads(content_text)
        except json.JSONDecodeError:
            logger.warning(f"Content structure response not valid JSON, using default")
            return get_default_template_structure()
        
    except Exception as e:
        logger.error(f"Error generating content structure: {str(e)}")
        raise

def generate_presentation_content(content_structure: Dict[str, Any],
                                financial_insights: Dict[str, Any],
                                template_key: str) -> Dict[str, Any]:
    """
    Generate detailed content for each slide.
    """
    try:
        presentation_content = {
            'slides': [],
            'metadata': content_structure.get('metadata', {})
        }
        
        # Get slide content prompt
        prompt = get_prompt('slide_content')
        
        # Generate content for each slide
        for slide in content_structure.get('slides', []):
            slide_content = generate_slide_content(
                slide,
                financial_insights,
                prompt
            )
            presentation_content['slides'].append(slide_content)
        
        return presentation_content
        
    except Exception as e:
        logger.error(f"Error generating presentation content: {str(e)}")
        raise

def generate_slide_content(slide: Dict[str, Any], 
                          financial_insights: Dict[str, Any],
                          prompt: str) -> Dict[str, Any]:
    """
    Generate content for a single slide.
    """
    try:
        response = bedrock_runtime.invoke_model(
            modelId='anthropic.claude-3-sonnet-20240229-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'messages': [{
                    'role': 'user',
                    'content': prompt.format(
                        slide_structure=json.dumps(slide),
                        financial_insights=json.dumps(financial_insights)
                    )
                }],
                'max_tokens': 2000,
                'temperature': 0.2
            })
        )
        
        result = json.loads(response['body'].read())
        content_text = result['content'][0]['text']
        
        # Try to parse as JSON, fallback to default slide content
        try:
            slide_content = json.loads(content_text)
        except json.JSONDecodeError:
            logger.warning(f"Slide content response not valid JSON, using default")
            slide_content = {
                'title': slide.get('title', f"Slide {slide.get('number', 1)}"),
                'content': content_text[:200] if content_text else "Generated content",
                'charts': [],
                'tables': [],
                'notes': ''
            }
        
        return {
            'slide_number': slide.get('number'),
            'slide_type': slide.get('type'),
            'title': slide_content.get('title'),
            'content': slide_content.get('content'),
            'charts': slide_content.get('charts', []),
            'tables': slide_content.get('tables', []),
            'notes': slide_content.get('notes', '')
        }
        
    except Exception as e:
        logger.error(f"Error generating slide content: {str(e)}")
        raise

def process_template(template_key: str, 
                    presentation_content: Dict[str, Any],
                    output_key: str):
    """
    Invoke template processor Lambda to generate final presentation.
    """
    try:
        lambda_client = boto3.client('lambda')
        
        response = lambda_client.invoke(
            FunctionName=f"scribbe-ai-{ENVIRONMENT}-template-processor",
            InvocationType='RequestResponse',
            Payload=json.dumps({
                'template_key': template_key,
                'presentation_content': presentation_content,
                'output_key': output_key
            })
        )
        
        result = json.loads(response['Payload'].read())
        if result.get('statusCode') != 200:
            raise Exception(f"Template processor failed: {result}")
            
    except Exception as e:
        logger.error(f"Error processing template: {str(e)}")
        raise

def get_prompt(prompt_name: str) -> str:
    """
    Retrieve prompt from S3.
    """
    try:
        obj = s3.get_object(
            Bucket=PROMPTS_BUCKET,
            Key=f"{prompt_name}.txt"
        )
        return obj['Body'].read().decode('utf-8')
        
    except Exception as e:
        logger.error(f"Error getting prompt {prompt_name}: {str(e)}")
        # Return default prompt
        return get_default_prompt(prompt_name)

def get_default_prompt(prompt_name: str) -> str:
    """
    Return default prompts if S3 prompts are not available.
    """
    prompts = {
        'financial_extraction': """Extract key financial data and insights from the following document analysis:
        {kb_response}
        
        Document: {document_key}
        
        Please provide a structured JSON response with:
        - key_metrics: Important financial metrics
        - trends: Identified trends
        - risks: Key risks
        - opportunities: Growth opportunities
        - summary: Executive summary
        """,
        
        'content_structure': """Create a presentation structure based on:
        Financial Insights: {financial_insights}
        Template Structure: {template_structure}
        User Instructions: {user_instructions}
        
        Return a JSON structure with slides array containing slide type, content outline, and data requirements.
        """,
        
        'slide_content': """Generate detailed content for this slide:
        Slide Structure: {slide_structure}
        Financial Insights: {financial_insights}
        
        Return JSON with title, content, charts, tables, and speaker notes.
        """
    }
    
    return prompts.get(prompt_name, "")

def save_metadata(presentation_id: str, metadata: Dict[str, Any]):
    """
    Save presentation metadata to S3.
    """
    try:
        s3.put_object(
            Bucket=OUTPUT_BUCKET,
            Key=f"{presentation_id}/metadata.json",
            Body=json.dumps(metadata, indent=2),
            ContentType='application/json'
        )
    except Exception as e:
        logger.error(f"Error saving metadata: {str(e)}")

def get_default_template_structure() -> Dict[str, Any]:
    """
    Return a default template structure for presentations.
    """
    return {
        "template_name": "default",
        "slides": [
            {
                "number": 1,
                "type": "title",
                "title": "Financial Analysis Presentation",
                "layout": "title_slide"
            },
            {
                "number": 2,
                "type": "overview",
                "title": "Executive Summary",
                "layout": "content"
            },
            {
                "number": 3,
                "type": "metrics",
                "title": "Key Financial Metrics", 
                "layout": "chart"
            },
            {
                "number": 4,
                "type": "trends",
                "title": "Financial Trends",
                "layout": "chart"
            },
            {
                "number": 5,
                "type": "conclusion",
                "title": "Conclusions & Recommendations",
                "layout": "content"
            }
        ],
        "metadata": {
            "author": "ScribbeAI",
            "version": "1.0"
        }
    }