"""
Simple LangChain-based Orchestrator
Uses minimal dependencies with web search capabilities
"""
import json
import os
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

# Load environment variables from .env file
try:
    import env_loader
    env_loader.load_env_file()
except ImportError:
    # Fallback if env_loader not available
    pass

# AWS imports
import boto3

# Tavily for web search
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False
    TavilyClient = None

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime', region_name='eu-west-1')

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'scribbe-ai-dev-output')
DOCUMENTS_BUCKET = os.environ.get('DOCUMENTS_BUCKET', 'scribbe-ai-dev-documents')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0')

# API Keys (loaded from .env file or environment variables)
TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY', '')


class SimpleOrchestrator:
    """Simple orchestrator with web search and basic AI routing"""
    
    def __init__(self):
        self.tavily = None
        if TAVILY_AVAILABLE and TAVILY_API_KEY:
            try:
                self.tavily = TavilyClient(api_key=TAVILY_API_KEY)
                logger.info("Tavily client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Tavily client: {str(e)}")
                self.tavily = None
    
    def _is_web_search_query(self, query: str) -> bool:
        """Determine if query needs web search"""
        web_indicators = [
            'current', 'latest', 'recent', 'news', 'today', 'yesterday',
            'this week', 'this month', 'this year', 'now', 'search',
            'find information', 'what happened', 'what is happening',
            'stock price', 'weather', 'trending'
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in web_indicators)
    
    def _is_presentation_request(self, query: str) -> bool:
        """Determine if query requests presentation creation"""
        presentation_indicators = [
            'presentation', 'powerpoint', 'ppt', 'slides', 'slide',
            'create presentation', 'make slides', 'generate presentation',
            'prezentácia', 'prezentaciu'
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in presentation_indicators)
    
    def _is_document_query(self, query: str) -> bool:
        """Determine if query is asking about documents"""
        document_indicators = [
            'document', 'file', 'uploaded', 'attachment', 'dokument',
            'what did i upload', 'analyze the file', 'tell me about',
            'summarize', 'explain the document'
        ]
        
        query_lower = query.lower()
        return any(indicator in query_lower for indicator in document_indicators)
    
    def _search_web(self, query: str) -> str:
        """Search the web using Tavily API"""
        if not self.tavily:
            return "Web search is not available. Please configure Tavily API key."
        
        try:
            logger.info(f"Performing web search for: {query}")
            
            # Search with Tavily
            response = self.tavily.search(
                query=query,
                max_results=5,
                include_answer=True,
                include_raw_content=False
            )
            
            # Format results
            result = ""
            if response.get('answer'):
                result = f"📍 **Answer:** {response['answer']}\n\n"
            
            if response.get('results'):
                result += "🔍 **Search Results:**\n"
                for idx, item in enumerate(response.get('results', [])[:5]):
                    result += f"\n**{idx + 1}. {item.get('title', 'No title')}**\n"
                    result += f"🔗 URL: {item.get('url', '')}\n"
                    result += f"📝 Summary: {item.get('content', '')[:200]}...\n"
            
            logger.info(f"Web search completed with {len(response.get('results', []))} results")
            return result
            
        except Exception as e:
            logger.error(f"Web search error: {str(e)}")
            return f"❌ Error searching web: {str(e)}"
    
    def _create_presentation(self, request: str) -> str:
        """Create PowerPoint presentation"""
        try:
            logger.info(f"Creating presentation for: {request}")
            
            # Import presentation module
            import presentation_agent
            
            # Create presentation agent
            ppt_agent = presentation_agent.PresentationAgent()
            result = ppt_agent.process({
                'instructions': request,
                'mode': 'modify',
                'template_key': 'PUBLIC IP South Plains (1).pptx'
            })
            
            if result['status'] == 'success':
                return f"✅ **Presentation created successfully!**\n📊 **File:** {result['presentation_name']}\n🔗 **Download:** {result['download_url']}"
            else:
                return f"❌ **Error creating presentation:** {result.get('message', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Presentation creation error: {str(e)}")
            return f"❌ **Error creating presentation:** {str(e)}"
    
    def _search_knowledge_base(self, query: str) -> str:
        """Search through uploaded documents in knowledge base"""
        try:
            logger.info(f"Searching knowledge base for: {query}")
            
            # List documents in knowledge base
            response = s3.list_objects_v2(
                Bucket=DOCUMENTS_BUCKET,
                Prefix='public/knowledge-base/',
                MaxKeys=20
            )
            
            if 'Contents' not in response:
                return "📚 No documents found in knowledge base."
            
            # Search through documents for relevant content
            relevant_content = []
            for obj in response['Contents']:
                if obj['Size'] > 5000000:  # Skip files larger than 5MB
                    continue
                    
                try:
                    # Download and read document
                    doc_response = s3.get_object(Bucket=DOCUMENTS_BUCKET, Key=obj['Key'])
                    content = doc_response['Body'].read().decode('utf-8', errors='ignore')
                    
                    # Simple relevance check
                    if any(word.lower() in content.lower() for word in query.split()):
                        doc_name = obj['Key'].split('/')[-1]
                        # Extract relevant snippet
                        snippet = self._extract_relevant_snippet(content, query, max_length=500)
                        if snippet:
                            relevant_content.append(f"**📄 From {doc_name}:**\n{snippet}")
                        
                        if len(relevant_content) >= 3:  # Limit to 3 most relevant snippets
                            break
                            
                except Exception as e:
                    logger.error(f"Error processing document {obj['Key']}: {str(e)}")
                    continue
            
            if relevant_content:
                return "📚 **Knowledge Base Search Results:**\n\n" + "\n\n".join(relevant_content)
            else:
                return f"📚 No relevant information found in knowledge base for: {query}"
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {str(e)}")
            return f"❌ Error searching knowledge base: {str(e)}"
    
    def _extract_relevant_snippet(self, content: str, query: str, max_length: int = 500) -> str:
        """Extract the most relevant snippet from content based on query"""
        query_words = query.lower().split()
        content_lower = content.lower()
        
        best_position = -1
        for word in query_words:
            position = content_lower.find(word)
            if position != -1 and (best_position == -1 or position < best_position):
                best_position = position
        
        if best_position == -1:
            return content[:max_length] + "..." if len(content) > max_length else content
        
        # Extract snippet around the found position
        start = max(0, best_position - 100)
        end = min(len(content), best_position + max_length)
        
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
            
        return snippet
    
    def _call_bedrock(self, prompt: str, context: str = "") -> str:
        """Call Bedrock Claude model"""
        try:
            system_prompt = """You are an AI assistant with access to web search and presentation creation capabilities. 
            Be helpful, accurate, and concise. Format your responses using markdown for better readability.
            
            Available capabilities:
            - Web search for current information
            - PowerPoint presentation creation
            - General question answering
            
            Always provide clear, well-structured responses."""
            
            if context:
                system_prompt += f"\n\nAdditional context:\n{context}"
            
            # Prepare the request
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "temperature": 0.7,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            # Call Bedrock
            response = bedrock.invoke_model(
                modelId=BEDROCK_MODEL_ID,
                body=json.dumps(request_body),
                contentType='application/json'
            )
            
            # Parse response
            response_body = json.loads(response['body'].read())
            return response_body.get('content', [{}])[0].get('text', 'No response generated')
            
        except Exception as e:
            logger.error(f"Bedrock error: {str(e)}")
            return f"❌ Error processing request: {str(e)}"
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process user request with intelligent routing"""
        try:
            user_input = request.get('instructions', '')
            files = request.get('files', [])
            
            logger.info(f"Simple Orchestrator processing: {user_input[:100]}...")
            
            # Add file context if files provided
            if files:
                file_context = f"\n\nUser has uploaded {len(files)} file(s): "
                for file_key in files:
                    file_context += f"\n- {file_key.split('/')[-1]}"
                user_input += file_context
            
            # Determine request type and route accordingly
            response_message = ""
            tools_used = []
            
            # Check for presentation request
            if self._is_presentation_request(user_input):
                logger.info("Routing to presentation creation")
                response_message = self._create_presentation(user_input)
                tools_used.append("Presentation_Creator")
            
            # Check for document/knowledge base query
            elif self._is_document_query(user_input) or files:
                logger.info("Routing to knowledge base search")
                kb_results = self._search_knowledge_base(user_input)
                tools_used.append("Knowledge_Base_Search")
                
                # Use Bedrock to analyze and respond based on documents
                bedrock_prompt = f"""User query: {user_input}

Knowledge base search results:
{kb_results}

Please provide a comprehensive answer based on the document content above. 
If no relevant documents were found, let the user know and offer to help with other questions."""
                
                response_message = self._call_bedrock(bedrock_prompt)
            
            # Check for web search request
            elif self._is_web_search_query(user_input):
                logger.info("Routing to web search")
                search_results = self._search_web(user_input)
                tools_used.append("Web_Search")
                
                # Use Bedrock to formulate a comprehensive answer
                bedrock_prompt = f"""User query: {user_input}

Web search results:
{search_results}

Please provide a comprehensive answer to the user's query based on the search results above. 
Be informative and cite the sources when relevant."""
                
                response_message = self._call_bedrock(bedrock_prompt)
            
            # Default to general AI response
            else:
                logger.info("Routing to general AI response")
                response_message = self._call_bedrock(user_input)
                tools_used.append("General_AI")
            
            return {
                'message': response_message,
                'status': 'success',
                'tools_used': tools_used,
                'agent': 'simple-orchestrator',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Simple Orchestrator error: {str(e)}")
            return {
                'error': 'Processing error',
                'message': str(e),
                'status': 'error',
                'agent': 'simple-orchestrator'
            }


# Create global orchestrator instance
orchestrator = SimpleOrchestrator()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for Simple orchestrator"""
    try:
        logger.info(f"Received event: {json.dumps(event)}")
        
        # Handle OPTIONS request for CORS
        if event.get('httpMethod') == 'OPTIONS':
            return {
                'statusCode': 200,
                'headers': {
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
                }
            }
        
        # Parse request body
        body = json.loads(event.get('body', '{}'))
        
        # Process request
        response = orchestrator.process_request(body)
        
        # Return response with CORS headers
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps(response)
        }
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}", exc_info=True)
        return {
            'statusCode': 500,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,GET'
            },
            'body': json.dumps({
                'error': 'Internal server error',
                'message': str(e)
            })
        }