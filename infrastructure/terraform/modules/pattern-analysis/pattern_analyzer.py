import json
import boto3
import os
import uuid
from datetime import datetime, timedelta
import logging
from collections import Counter
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
bedrock_client = boto3.client('bedrock-agent-runtime')

patterns_table = dynamodb.Table(os.environ['PATTERNS_TABLE_NAME'])
findings_table = dynamodb.Table(os.environ['FINDINGS_TABLE_NAME'])
knowledge_base_id = os.environ['KNOWLEDGE_BASE_ID']

def lambda_handler(event, context):
    """
    Analyze patterns from uploaded documents and client interactions
    """
    
    try:
        logger.info("Starting pattern analysis")
        
        # Analyze different types of patterns
        document_patterns = analyze_document_patterns()
        query_patterns = analyze_query_patterns()
        client_behavior_patterns = analyze_client_behavior()
        
        # Store discovered patterns
        patterns_stored = 0
        for pattern_type, patterns in {
            'document_content': document_patterns,
            'user_queries': query_patterns,
            'client_behavior': client_behavior_patterns
        }.items():
            
            for pattern in patterns:
                store_pattern(pattern_type, pattern)
                patterns_stored += 1
        
        # Generate insights summary
        insights = generate_insights_summary()
        
        logger.info(f"Pattern analysis completed. Stored {patterns_stored} patterns")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Pattern analysis completed successfully',
                'patterns_stored': patterns_stored,
                'insights': insights,
                'timestamp': datetime.utcnow().isoformat()
            })
        }
        
    except Exception as e:
        logger.error(f"Error in pattern analysis: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'message': 'Failed to complete pattern analysis'
            })
        }

def analyze_document_patterns():
    """
    Analyze patterns in uploaded documents using Bedrock Knowledge Base
    """
    patterns = []
    
    try:
        # Query knowledge base for common themes
        common_themes_query = "What are the most common themes, topics, and subjects discussed in the uploaded documents?"
        
        response = bedrock_client.retrieve_and_generate(
            input={
                'text': common_themes_query
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': knowledge_base_id,
                    'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0'
                }
            }
        )
        
        if response.get('output', {}).get('text'):
            themes_text = response['output']['text']
            
            # Extract patterns from the response
            patterns.append({
                'description': 'Common document themes analysis',
                'details': themes_text,
                'confidence_score': 0.8,
                'source': 'bedrock_analysis',
                'metadata': {
                    'analysis_type': 'theme_extraction',
                    'document_count': 'multiple'
                }
            })
        
        # Analyze financial data patterns if applicable
        financial_query = "What financial metrics, trends, or data patterns appear most frequently in the documents?"
        
        financial_response = bedrock_client.retrieve_and_generate(
            input={
                'text': financial_query
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': knowledge_base_id,
                    'modelArn': 'arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0'
                }
            }
        )
        
        if financial_response.get('output', {}).get('text'):
            financial_text = financial_response['output']['text']
            
            patterns.append({
                'description': 'Financial data patterns',
                'details': financial_text,
                'confidence_score': 0.75,
                'source': 'bedrock_analysis',
                'metadata': {
                    'analysis_type': 'financial_patterns',
                    'focus_area': 'financial_metrics'
                }
            })
            
    except Exception as e:
        logger.error(f"Error analyzing document patterns: {str(e)}")
    
    return patterns

def analyze_query_patterns():
    """
    Analyze patterns in user queries and interactions
    """
    patterns = []
    
    try:
        # This would typically analyze logged user queries
        # For now, we'll simulate common query patterns
        
        common_query_types = [
            {
                'description': 'Presentation generation requests',
                'pattern': 'Users frequently request PowerPoint presentations from financial documents',
                'confidence_score': 0.9,
                'frequency': 'high'
            },
            {
                'description': 'Data analysis queries',
                'pattern': 'Users ask for trend analysis and data interpretation',
                'confidence_score': 0.85,
                'frequency': 'medium'
            },
            {
                'description': 'Document summarization',
                'pattern': 'Requests for executive summaries of uploaded documents',
                'confidence_score': 0.8,
                'frequency': 'high'
            }
        ]
        
        for query_pattern in common_query_types:
            patterns.append({
                'description': query_pattern['description'],
                'details': query_pattern['pattern'],
                'confidence_score': query_pattern['confidence_score'],
                'source': 'query_analysis',
                'metadata': {
                    'analysis_type': 'user_behavior',
                    'frequency': query_pattern['frequency']
                }
            })
            
    except Exception as e:
        logger.error(f"Error analyzing query patterns: {str(e)}")
    
    return patterns

def analyze_client_behavior():
    """
    Analyze client behavior patterns and usage trends
    """
    patterns = []
    
    try:
        # This would analyze actual usage data from audit logs
        # For now, we'll create example patterns
        
        behavior_patterns = [
            {
                'description': 'Peak usage times',
                'pattern': 'Highest activity during business hours (9 AM - 5 PM)',
                'confidence_score': 0.9,
                'impact': 'high'
            },
            {
                'description': 'File upload patterns',
                'pattern': 'Users typically upload multiple documents in batches',
                'confidence_score': 0.8,
                'impact': 'medium'
            },
            {
                'description': 'Feature preferences',
                'pattern': 'Presentation generation is the most used feature',
                'confidence_score': 0.85,
                'impact': 'high'
            }
        ]
        
        for behavior in behavior_patterns:
            patterns.append({
                'description': behavior['description'],
                'details': behavior['pattern'],
                'confidence_score': behavior['confidence_score'],
                'source': 'behavior_analysis',
                'metadata': {
                    'analysis_type': 'usage_patterns',
                    'business_impact': behavior['impact']
                }
            })
            
    except Exception as e:
        logger.error(f"Error analyzing client behavior: {str(e)}")
    
    return patterns

def store_pattern(pattern_type, pattern):
    """
    Store a discovered pattern in DynamoDB
    """
    try:
        pattern_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        item = {
            'pattern_id': pattern_id,
            'discovered_at': timestamp,
            'pattern_type': pattern_type,
            'description': pattern['description'],
            'details': pattern['details'],
            'confidence_score': pattern['confidence_score'],
            'source': pattern['source'],
            'metadata': json.dumps(pattern.get('metadata', {})),
            'expires_at': int((datetime.utcnow() + timedelta(days=365)).timestamp())  # 1 year TTL
        }
        
        patterns_table.put_item(Item=item)
        logger.info(f"Stored pattern: {pattern['description']}")
        
    except Exception as e:
        logger.error(f"Error storing pattern: {str(e)}")

def generate_insights_summary():
    """
    Generate a summary of key insights from pattern analysis
    """
    try:
        # Query recent patterns
        response = patterns_table.scan(
            FilterExpression='discovered_at > :timestamp',
            ExpressionAttributeValues={
                ':timestamp': (datetime.utcnow() - timedelta(days=30)).isoformat()
            },
            Limit=50
        )
        
        patterns = response.get('Items', [])
        
        # Analyze pattern types
        pattern_types = Counter([p['pattern_type'] for p in patterns])
        avg_confidence = sum([float(p['confidence_score']) for p in patterns]) / len(patterns) if patterns else 0
        
        insights = {
            'total_patterns': len(patterns),
            'pattern_types': dict(pattern_types),
            'average_confidence': round(avg_confidence, 2),
            'top_patterns': [
                {
                    'description': p['description'],
                    'confidence': float(p['confidence_score'])
                }
                for p in sorted(patterns, key=lambda x: float(x['confidence_score']), reverse=True)[:5]
            ]
        }
        
        return insights
        
    except Exception as e:
        logger.error(f"Error generating insights summary: {str(e)}")
        return {}

def store_client_finding(client_id, category, finding_data):
    """
    Store a client-specific finding for trend analysis
    """
    try:
        finding_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        item = {
            'finding_id': finding_id,
            'created_at': timestamp,
            'client_id': client_id,
            'category': category,
            'data': json.dumps(finding_data),
            'expires_at': int((datetime.utcnow() + timedelta(days=730)).timestamp())  # 2 years TTL
        }
        
        findings_table.put_item(Item=item)
        logger.info(f"Stored client finding for {client_id}")
        
    except Exception as e:
        logger.error(f"Error storing client finding: {str(e)}")