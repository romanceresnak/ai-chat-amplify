# LangChain Integration Setup Guide

## Overview
This guide explains how to set up and configure the LangChain-based orchestrator with advanced AI capabilities including web search, document parsing, and intelligent agent routing.

## Features
- **LangChain Framework**: Modern agent orchestration with memory and tools
- **Web Search**: Real-time information retrieval using Tavily API
- **Advanced Document Parsing**: Using Unstructured library for better document analysis
- **Vector Search**: FAISS-based semantic search in knowledge base
- **Intelligent Routing**: AI-powered request routing to appropriate agents

## Prerequisites

### API Keys Required
1. **Tavily API Key**: For web search functionality
   - Sign up at https://tavily.com
   - Get your API key from the dashboard
   
2. **SerpAPI Key** (Optional): Alternative web search
   - Sign up at https://serpapi.com
   - Get your API key

## Configuration

### 1. Environment Variables

#### For Lambda (Production)
Update your Terraform configuration or AWS Lambda console:
```hcl
environment {
  variables = {
    USE_LANGCHAIN   = "true"
    TAVILY_API_KEY  = "your-tavily-api-key"
    SERPAPI_API_KEY = "your-serpapi-key"  # Optional
  }
}
```

#### For Frontend
Create `.env.local` in the frontend directory:
```bash
NEXT_PUBLIC_USE_LANGCHAIN=true
NEXT_PUBLIC_ENABLE_WEB_SEARCH=true
NEXT_PUBLIC_ENABLE_DOCUMENT_KB=true
```

### 2. AWS Secrets Manager (Recommended for Production)
Store API keys securely:
```bash
aws secretsmanager create-secret \
  --name scribbe-ai/langchain-api-keys \
  --secret-string '{
    "tavily_api_key": "your-key",
    "serpapi_api_key": "your-key"
  }'
```

## Usage

### 1. Enable LangChain Orchestrator

#### Option A: Per Request
Include `use_langchain: true` in your API request:
```javascript
const response = await fetch('/api/presentations', {
  method: 'POST',
  body: JSON.stringify({
    instructions: "Search for latest AI trends",
    use_langchain: true
  })
});
```

#### Option B: Globally
Set environment variable `USE_LANGCHAIN=true` in Lambda configuration.

### 2. Available Tools

#### Web Search
```
"Search for latest news about OpenAI"
"What are the current stock prices for tech companies?"
"Find information about climate change solutions"
```

#### Document Analysis
```
"Analyze this contract and extract key terms"
"Summarize the uploaded PDF and save to knowledge base"
"Extract financial data from this report"
```

#### Presentation Creation
```
"Create a presentation about Q2 results with latest market data"
"Generate slides comparing our product with competitors"
```

#### Knowledge Base Search
```
"What information do we have about project X?"
"Find all documents related to financial planning"
```

## Architecture

```
User Request
    ↓
LangChain Orchestrator
    ↓
AI Router (Claude)
    ↓
Tools Selection
    ├── Web Search (Tavily)
    ├── Document Parser (Unstructured)
    ├── Presentation Creator
    ├── Knowledge Base (FAISS)
    └── Financial Data
    ↓
Response with Sources
```

## Advanced Features

### 1. Memory Management
The LangChain orchestrator maintains conversation memory:
- Remembers context across interactions
- Can reference previous queries
- Maintains user preferences

### 2. Tool Chaining
Multiple tools can be used in sequence:
- Search web → Extract data → Create presentation
- Analyze document → Save to KB → Generate summary

### 3. Error Handling
- Fallback to original orchestrator if LangChain fails
- Graceful degradation when APIs unavailable
- Detailed error logging

## Monitoring

### CloudWatch Logs
Monitor LangChain usage:
```
Filter: "LangChain Orchestrator"
Filter: "Tools used:"
```

### Metrics to Track
- Tool usage frequency
- API call success rates
- Response times
- Token usage

## Cost Considerations

### API Costs
- Tavily: ~$0.001 per search
- SerpAPI: ~$0.002 per search
- Bedrock: Standard Claude pricing

### Optimization Tips
1. Cache frequent searches
2. Use knowledge base before web search
3. Batch similar requests
4. Set appropriate token limits

## Troubleshooting

### Common Issues

1. **"LangChain not available"**
   - Check Lambda layer includes all dependencies
   - Verify requirements.txt is up to date

2. **"Web search not configured"**
   - Ensure TAVILY_API_KEY is set
   - Check API key validity

3. **"Document parsing failed"**
   - Verify Unstructured library installation
   - Check file format compatibility

## Future Enhancements

1. **Univer Grid Integration**: Financial data API
2. **SlideSpeak API**: Advanced presentation features
3. **Llama Index**: Better document indexing
4. **Firecrawl**: Web scraping capabilities
5. **Perplexity API**: Alternative search provider

## Security Best Practices

1. Never commit API keys to repository
2. Use AWS Secrets Manager for production
3. Implement rate limiting
4. Monitor API usage for anomalies
5. Rotate API keys regularly

## Support

For issues or questions:
- Check CloudWatch logs
- Review this documentation
- Contact development team