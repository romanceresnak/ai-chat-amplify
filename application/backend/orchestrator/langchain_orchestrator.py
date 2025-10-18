"""
LangChain-based Multi-Agent Orchestrator
Implements modern AI agent system using LangChain framework
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

# LangChain imports
from langchain.agents import Tool, AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain_aws import ChatBedrock
from langchain.memory import ConversationBufferMemory
from langchain.schema import Document
from langchain_community.utilities import SerpAPIWrapper
from langchain_community.document_loaders import UnstructuredFileLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import BedrockEmbeddings

# Tavily for web search
from tavily import TavilyClient

# Initialize logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3 = boto3.client('s3')
bedrock = boto3.client('bedrock-runtime', region_name='us-east-1')

# Environment variables
ENVIRONMENT = os.environ.get('ENVIRONMENT', 'dev')
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET', 'scribbe-ai-dev-output')
DOCUMENTS_BUCKET = os.environ.get('DOCUMENTS_BUCKET', 'scribbe-ai-dev-documents')
BEDROCK_MODEL_ID = os.environ.get('BEDROCK_MODEL_ID', 'eu.anthropic.claude-3-5-sonnet-20240620-v1:0')

# API Keys (loaded from .env file or environment variables)
TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY', '')
SERPAPI_API_KEY = os.environ.get('SERPAPI_API_KEY', '')


class LangChainOrchestrator:
    """Main orchestrator using LangChain framework"""
    
    def __init__(self):
        # Initialize Bedrock Chat model
        self.llm = ChatBedrock(
            model_id=BEDROCK_MODEL_ID,
            client=bedrock,
            model_kwargs={
                "temperature": 0.7,
                "max_tokens": 2000
            }
        )
        
        # Initialize embeddings for vector store
        self.embeddings = BedrockEmbeddings(
            client=bedrock,
            model_id="amazon.titan-embed-text-v1"
        )
        
        # Initialize memory
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # Initialize tools
        self.tools = self._initialize_tools()
        
        # Create main agent
        self.agent = self._create_main_agent()
        
    def _initialize_tools(self) -> List[Tool]:
        """Initialize all available tools"""
        tools = []
        
        # Web Search Tool (Tavily)
        if TAVILY_API_KEY:
            tavily_tool = Tool(
                name="Web_Search",
                func=self._tavily_search,
                description="Search the web for current information, news, and data. Use this when you need real-time or recent information."
            )
            tools.append(tavily_tool)
        
        # Document Analysis Tool
        doc_tool = Tool(
            name="Document_Analyzer",
            func=self._analyze_document,
            description="Analyze and extract information from documents. Use this when user uploads files or asks to analyze documents."
        )
        tools.append(doc_tool)
        
        # Presentation Tool
        ppt_tool = Tool(
            name="Presentation_Creator",
            func=self._create_presentation,
            description="Create or modify PowerPoint presentations. Use this when user asks for slides, presentations, or PowerPoint files."
        )
        tools.append(ppt_tool)
        
        # Knowledge Base Search Tool
        kb_tool = Tool(
            name="Knowledge_Base_Search",
            func=self._search_knowledge_base,
            description="Search internal knowledge base for stored information. Use this for questions about previously stored documents."
        )
        tools.append(kb_tool)
        
        # Financial Data Tool (placeholder for Univer Grid)
        finance_tool = Tool(
            name="Financial_Data",
            func=self._get_financial_data,
            description="Get financial information about companies including metrics, ratios, and performance data."
        )
        tools.append(finance_tool)
        
        return tools
    
    def _create_main_agent(self) -> AgentExecutor:
        """Create the main orchestrating agent"""
        
        # Define the agent prompt
        agent_prompt = PromptTemplate(
            input_variables=["input", "tools", "tool_names", "agent_scratchpad", "chat_history"],
            template="""You are an AI assistant with access to multiple specialized tools. Your goal is to help users with their requests by intelligently using the available tools.

Available tools:
{tools}

Tool names: {tool_names}

Previous conversation:
{chat_history}

Current request: {input}

To use a tool, you must use the following format:
Thought: I need to [explain what you're going to do]
Action: [tool_name]
Action Input: [input for the tool]
Observation: [tool output]

You can use multiple tools if needed. After you have all the information you need, provide a final answer.

Thought: Let me analyze this request and determine the best approach.
{agent_scratchpad}"""
        )
        
        # Create the agent
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=agent_prompt
        )
        
        # Create agent executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=True,
            return_intermediate_steps=True,
            handle_parsing_errors=True,
            max_iterations=5
        )
        
        return agent_executor
    
    def _tavily_search(self, query: str) -> str:
        """Search the web using Tavily API"""
        try:
            if not TAVILY_API_KEY:
                return "Web search is not configured. Please provide Tavily API key."
            
            tavily = TavilyClient(api_key=TAVILY_API_KEY)
            
            # Search with Tavily
            response = tavily.search(
                query=query,
                max_results=5,
                include_answer=True,
                include_raw_content=False
            )
            
            # Format results
            if response.get('answer'):
                result = f"Answer: {response['answer']}\n\n"
            else:
                result = ""
            
            result += "Search Results:\n"
            for idx, item in enumerate(response.get('results', [])[:5]):
                result += f"\n{idx + 1}. {item.get('title', 'No title')}\n"
                result += f"   URL: {item.get('url', '')}\n"
                result += f"   Summary: {item.get('content', '')[:200]}...\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Tavily search error: {str(e)}")
            return f"Error searching web: {str(e)}"
    
    def _analyze_document(self, file_info: Dict[str, Any]) -> str:
        """Analyze document using Unstructured library"""
        try:
            file_key = file_info.get('key', '')
            bucket = file_info.get('bucket', 'scribbe-ai-dev-storage')
            
            # Download file from S3
            local_path = f"/tmp/{file_key.split('/')[-1]}"
            s3.download_file(bucket, file_key, local_path)
            
            # Load and parse with Unstructured
            loader = UnstructuredFileLoader(local_path)
            documents = loader.load()
            
            # Split documents for better processing
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200
            )
            splits = text_splitter.split_documents(documents)
            
            # Create temporary vector store for querying
            vectorstore = FAISS.from_documents(splits, self.embeddings)
            
            # Extract key information
            summary_prompt = """Analyze this document and provide:
            1. Document type and purpose
            2. Key findings or main points
            3. Important dates, numbers, or metrics
            4. Recommendations or conclusions
            """
            
            # Use LLM to summarize
            response = self.llm.invoke(f"{summary_prompt}\n\nDocument content:\n{documents[0].page_content[:3000]}")
            
            # Clean up
            os.remove(local_path)
            
            # Option to save to knowledge base
            if file_info.get('save_to_kb', False):
                self._save_to_knowledge_base(documents, file_key)
                response += "\n\n✅ Document saved to knowledge base for future reference."
            
            return response.content
            
        except Exception as e:
            logger.error(f"Document analysis error: {str(e)}")
            return f"Error analyzing document: {str(e)}"
    
    def _create_presentation(self, request: Dict[str, Any]) -> str:
        """Create or modify PowerPoint presentation"""
        try:
            instructions = request.get('instructions', '')
            
            # Import presentation module
            import presentation_agent
            
            # Create presentation agent
            ppt_agent = presentation_agent.PresentationAgent()
            result = ppt_agent.process({
                'instructions': instructions,
                'mode': request.get('mode', 'modify'),
                'template_key': request.get('template_key', 'PUBLIC IP South Plains (1).pptx')
            })
            
            if result['status'] == 'success':
                return f"✅ Presentation created successfully!\n📊 File: {result['presentation_name']}\n🔗 Download: {result['download_url']}"
            else:
                return f"❌ Error creating presentation: {result.get('message', 'Unknown error')}"
                
        except Exception as e:
            logger.error(f"Presentation creation error: {str(e)}")
            return f"Error creating presentation: {str(e)}"
    
    def _search_knowledge_base(self, query: str) -> str:
        """Search through stored documents in knowledge base"""
        try:
            # List documents in knowledge base
            response = s3.list_objects_v2(
                Bucket=DOCUMENTS_BUCKET,
                Prefix='knowledge-base/',
                MaxKeys=20
            )
            
            if 'Contents' not in response:
                return "No documents found in knowledge base."
            
            # Load documents and create vector store
            documents = []
            for obj in response['Contents']:
                try:
                    doc_response = s3.get_object(Bucket=DOCUMENTS_BUCKET, Key=obj['Key'])
                    content = doc_response['Body'].read().decode('utf-8', errors='ignore')
                    doc = Document(
                        page_content=content[:5000],  # Limit size
                        metadata={
                            'source': obj['Key'],
                            'modified': obj['LastModified'].isoformat()
                        }
                    )
                    documents.append(doc)
                except Exception as e:
                    logger.error(f"Error loading KB document {obj['Key']}: {str(e)}")
                    continue
            
            if not documents:
                return "Could not load any documents from knowledge base."
            
            # Create vector store and search
            vectorstore = FAISS.from_documents(documents, self.embeddings)
            results = vectorstore.similarity_search(query, k=3)
            
            # Format results
            response = "📚 Knowledge Base Search Results:\n\n"
            for idx, doc in enumerate(results):
                source = doc.metadata.get('source', 'Unknown').split('/')[-1]
                response += f"{idx + 1}. From {source}:\n"
                response += f"   {doc.page_content[:300]}...\n\n"
            
            return response
            
        except Exception as e:
            logger.error(f"Knowledge base search error: {str(e)}")
            return f"Error searching knowledge base: {str(e)}"
    
    def _get_financial_data(self, company_info: str) -> str:
        """Get financial data (placeholder for Univer Grid integration)"""
        try:
            # This is a placeholder - in production, integrate with Univer Grid API
            # For now, we can use web search for financial information
            
            if "financial" in company_info.lower() or "revenue" in company_info.lower():
                return self._tavily_search(f"{company_info} financial results revenue metrics")
            else:
                return "Financial data integration pending. Please specify what financial information you need."
                
        except Exception as e:
            logger.error(f"Financial data error: {str(e)}")
            return f"Error getting financial data: {str(e)}"
    
    def _save_to_knowledge_base(self, documents: List[Document], original_key: str) -> bool:
        """Save parsed documents to knowledge base"""
        try:
            timestamp = datetime.utcnow().isoformat()
            filename = original_key.split('/')[-1]
            kb_key = f"knowledge-base/{timestamp}_{filename}"
            
            # Combine all document content
            content = "\n\n".join([doc.page_content for doc in documents])
            
            # Save to S3
            s3.put_object(
                Bucket=DOCUMENTS_BUCKET,
                Key=kb_key,
                Body=content.encode('utf-8'),
                ContentType='text/plain',
                Metadata={
                    'source': 'langchain-orchestrator',
                    'original-file': original_key,
                    'indexed-at': timestamp,
                    'chunks': str(len(documents))
                }
            )
            
            logger.info(f"Saved to knowledge base: {kb_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving to knowledge base: {str(e)}")
            return False
    
    def process_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Process user request through LangChain agent"""
        try:
            user_input = request.get('instructions', '')
            files = request.get('files', [])
            
            # Add file context to input if files are provided
            if files:
                file_context = f"\n\nUser has uploaded {len(files)} file(s): "
                for file_key in files:
                    file_context += f"\n- {file_key.split('/')[-1]}"
                user_input += file_context
            
            logger.info(f"LangChain Orchestrator processing: {user_input[:100]}...")
            
            # Run agent
            result = self.agent.invoke({"input": user_input})
            
            # Extract response
            output = result.get('output', '')
            intermediate_steps = result.get('intermediate_steps', [])
            
            # Log tool usage
            tools_used = []
            for step in intermediate_steps:
                if len(step) >= 2:
                    action = step[0]
                    tools_used.append(action.tool)
            
            logger.info(f"Tools used: {tools_used}")
            
            return {
                'message': output,
                'status': 'success',
                'tools_used': list(set(tools_used)),
                'agent': 'langchain-orchestrator',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"LangChain Orchestrator error: {str(e)}")
            return {
                'error': 'Processing error',
                'message': str(e),
                'status': 'error',
                'agent': 'langchain-orchestrator'
            }


# Create global orchestrator instance
orchestrator = LangChainOrchestrator()


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler for LangChain orchestrator"""
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