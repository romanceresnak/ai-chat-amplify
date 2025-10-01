import json
import boto3
import os
import logging
from typing import Dict, Any, List
import re

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
bedrock_runtime = boto3.client('bedrock-runtime')
bedrock_agent = boto3.client('bedrock-agent-runtime')

# Environment variables
ENVIRONMENT = os.environ['ENVIRONMENT']
BEDROCK_KB_ID = os.environ['BEDROCK_KB_ID']

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Generate specific content sections using Bedrock models.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Parse request
        content_type = event.get('content_type')
        context_data = event.get('context_data', {})
        requirements = event.get('requirements', {})
        
        if not content_type:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': 'Missing content_type parameter'
                })
            }
        
        # Route to appropriate content generator
        if content_type == 'executive_summary':
            content = generate_executive_summary(context_data, requirements)
        elif content_type == 'financial_analysis':
            content = generate_financial_analysis(context_data, requirements)
        elif content_type == 'market_overview':
            content = generate_market_overview(context_data, requirements)
        elif content_type == 'risk_assessment':
            content = generate_risk_assessment(context_data, requirements)
        elif content_type == 'recommendations':
            content = generate_recommendations(context_data, requirements)
        elif content_type == 'charts':
            content = generate_chart_specifications(context_data, requirements)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'error': f'Unknown content_type: {content_type}'
                })
            }
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'content_type': content_type,
                'content': content
            })
        }
        
    except Exception as e:
        logger.error(f"Error in content generator: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }

def generate_executive_summary(context_data: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate executive summary content.
    """
    try:
        prompt = f"""Generate a professional executive summary for a financial presentation based on the following data:

Context: {json.dumps(context_data)}
Requirements: {json.dumps(requirements)}

The summary should include:
1. Key highlights (3-5 bullet points)
2. Main financial metrics
3. Strategic implications
4. Recommended actions

Format the response as JSON with the following structure:
{{
    "title": "Executive Summary",
    "highlights": ["highlight1", "highlight2", ...],
    "key_metrics": {{"metric_name": "value", ...}},
    "strategic_implications": "text",
    "recommendations": ["rec1", "rec2", ...]
}}"""

        response = invoke_bedrock_model(prompt, temperature=0.3)
        return json.loads(response)
        
    except Exception as e:
        logger.error(f"Error generating executive summary: {str(e)}")
        raise

def generate_financial_analysis(context_data: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate detailed financial analysis content.
    """
    try:
        prompt = f"""Perform a comprehensive financial analysis based on:

Financial Data: {json.dumps(context_data.get('financial_data', {}))}
Requirements: {json.dumps(requirements)}

Include:
1. Revenue analysis with YoY growth
2. Profitability metrics
3. Cost structure analysis
4. Cash flow assessment
5. Key ratios and benchmarks

Format as JSON with:
{{
    "revenue_analysis": {{
        "current_revenue": "",
        "yoy_growth": "",
        "breakdown": {{}},
        "trends": []
    }},
    "profitability": {{
        "gross_margin": "",
        "operating_margin": "",
        "net_margin": "",
        "ebitda": ""
    }},
    "cost_structure": {{
        "cogs_percentage": "",
        "opex_breakdown": {{}},
        "efficiency_metrics": {{}}
    }},
    "cash_flow": {{
        "operating_cf": "",
        "free_cf": "",
        "burn_rate": ""
    }},
    "key_ratios": {{}}
}}"""

        response = invoke_bedrock_model(prompt, temperature=0.1)
        return json.loads(response)
        
    except Exception as e:
        logger.error(f"Error generating financial analysis: {str(e)}")
        raise

def generate_market_overview(context_data: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate market overview and competitive analysis.
    """
    try:
        prompt = f"""Create a market overview based on:

Market Data: {json.dumps(context_data.get('market_data', {}))}
Company Position: {json.dumps(context_data.get('company_position', {}))}
Requirements: {json.dumps(requirements)}

Include:
1. Market size and growth
2. Key trends and drivers
3. Competitive landscape
4. Market share analysis
5. Future outlook

Format as JSON with comprehensive market insights."""

        response = invoke_bedrock_model(prompt, temperature=0.2)
        return json.loads(response)
        
    except Exception as e:
        logger.error(f"Error generating market overview: {str(e)}")
        raise

def generate_risk_assessment(context_data: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate risk assessment and mitigation strategies.
    """
    try:
        prompt = f"""Conduct a risk assessment based on:

Company Data: {json.dumps(context_data)}
Requirements: {json.dumps(requirements)}

Analyze:
1. Market risks
2. Operational risks
3. Financial risks
4. Regulatory risks
5. Technology risks

For each risk category, provide:
- Risk description
- Probability (High/Medium/Low)
- Impact (High/Medium/Low)
- Mitigation strategies

Format as structured JSON."""

        response = invoke_bedrock_model(prompt, temperature=0.2)
        return json.loads(response)
        
    except Exception as e:
        logger.error(f"Error generating risk assessment: {str(e)}")
        raise

def generate_recommendations(context_data: Dict[str, Any], requirements: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate strategic recommendations.
    """
    try:
        # Query knowledge base for similar cases
        kb_insights = query_knowledge_base(
            f"Strategic recommendations for companies with profile: {json.dumps(context_data.get('company_profile', {}))}"
        )
        
        prompt = f"""Generate strategic recommendations based on:

Analysis Results: {json.dumps(context_data)}
Knowledge Base Insights: {json.dumps(kb_insights)}
Requirements: {json.dumps(requirements)}

Provide:
1. Short-term recommendations (0-6 months)
2. Medium-term recommendations (6-18 months)
3. Long-term recommendations (18+ months)
4. Quick wins
5. Investment priorities

Each recommendation should include:
- Action item
- Expected impact
- Resources required
- Timeline
- Success metrics

Format as actionable JSON structure."""

        response = invoke_bedrock_model(prompt, temperature=0.3)
        return json.loads(response)
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        raise

def generate_chart_specifications(context_data: Dict[str, Any], requirements: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Generate specifications for charts and visualizations.
    """
    try:
        prompt = f"""Design data visualizations for the following data:

Data: {json.dumps(context_data)}
Requirements: {json.dumps(requirements)}

For each chart, specify:
1. Chart type (bar, line, pie, scatter, waterfall, etc.)
2. Data series
3. Axes labels
4. Title
5. Color scheme
6. Key insights to highlight

Return an array of chart specifications in JSON format:
[
    {{
        "chart_type": "",
        "title": "",
        "data": [],
        "axes": {{"x": "", "y": ""}},
        "colors": [],
        "insights": []
    }}
]"""

        response = invoke_bedrock_model(prompt, temperature=0.2)
        return json.loads(response)
        
    except Exception as e:
        logger.error(f"Error generating chart specifications: {str(e)}")
        raise

def invoke_bedrock_model(prompt: str, temperature: float = 0.3, max_tokens: int = 4000) -> str:
    """
    Invoke Bedrock model with the given prompt.
    """
    try:
        response = bedrock_runtime.invoke_model(
            modelId='eu.anthropic.claude-3-5-sonnet-20240620-v1:0',
            contentType='application/json',
            accept='application/json',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'messages': [{
                    'role': 'user',
                    'content': prompt
                }],
                'max_tokens': max_tokens,
                'temperature': temperature
            })
        )
        
        result = json.loads(response['body'].read())
        return result['content'][0]['text']
        
    except Exception as e:
        logger.error(f"Error invoking Bedrock model: {str(e)}")
        raise

def query_knowledge_base(query: str) -> Dict[str, Any]:
    """
    Query the Bedrock knowledge base for relevant information.
    """
    try:
        response = bedrock_agent.retrieve(
            knowledgeBaseId=BEDROCK_KB_ID,
            retrievalQuery={
                'text': query
            },
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': 5
                }
            }
        )
        
        results = []
        for result in response.get('retrievalResults', []):
            results.append({
                'content': result.get('content', {}).get('text', ''),
                'score': result.get('score', 0),
                'metadata': result.get('metadata', {})
            })
        
        return {'results': results}
        
    except Exception as e:
        logger.error(f"Error querying knowledge base: {str(e)}")
        return {'results': []}

def validate_json_response(response: str) -> str:
    """
    Validate and clean JSON response from the model.
    """
    try:
        # Remove any markdown code blocks
        response = re.sub(r'```json\s*', '', response)
        response = re.sub(r'```\s*', '', response)
        
        # Try to parse JSON
        json.loads(response)
        return response
        
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        json_match = re.search(r'\{.*\}', response, re.DOTALL)
        if json_match:
            try:
                json.loads(json_match.group())
                return json_match.group()
            except:
                pass
        
        # If all else fails, return a default structure
        logger.warning(f"Could not parse JSON response: {response[:200]}...")
        return json.dumps({"error": "Could not parse response", "raw": response[:500]})