# Environment Configuration Guide

## 📋 Overview
This project uses environment variables to manage configuration securely. API keys and sensitive information are stored in `.env` files that are **not committed** to version control.

## 🚀 Quick Setup

### 1. Create your .env file
```bash
# Copy the example template
cp .env.example .env

# Edit with your API keys
nano .env
```

### 2. Get API Keys

#### Tavily (Web Search)
1. Go to https://tavily.com
2. Sign up for free account
3. Get API key from dashboard
4. Add to .env: `TAVILY_API_KEY=tvly-your-actual-key`

#### SerpAPI (Alternative Web Search)
1. Go to https://serpapi.com  
2. Sign up for account
3. Get API key from dashboard
4. Add to .env: `SERPAPI_API_KEY=your-actual-key`

### 3. Configure Features
```bash
# Enable LangChain orchestrator
USE_LANGCHAIN=true

# Enable web search
ENABLE_WEB_SEARCH=true

# Enable document knowledge base
ENABLE_DOCUMENT_KB=true
```

## 📁 File Structure
```
Project/
├── .env                    # Your local config (not in git)
├── .env.example           # Template (committed to git)
├── .gitignore            # Ensures .env is not committed
└── scripts/
    └── deploy_with_env.py # Deploy script using .env
```

## 🔒 Security Features

### Environment File Protection
- `.env` files are automatically ignored by git
- Sensitive keys are masked in logs
- Fallback to system environment variables

### Safe Deployment
```bash
# Deploy Lambda with environment variables
python scripts/deploy_with_env.py
```

## ⚙️ Configuration Options

### Core Settings
```bash
# AWS Configuration
AWS_REGION=eu-west-1
ENVIRONMENT=dev

# LangChain Features
USE_LANGCHAIN=true                    # Enable/disable LangChain
TAVILY_API_KEY=your-key              # Web search
SERPAPI_API_KEY=your-key             # Alternative search

# Bedrock Configuration  
BEDROCK_MODEL_ID=eu.anthropic.claude-3-5-sonnet-20240620-v1:0
```

### S3 Buckets
```bash
OUTPUT_BUCKET=scribbe-ai-dev-output
DOCUMENTS_BUCKET=scribbe-ai-dev-documents
TEMPLATES_BUCKET=scribbe-ai-dev-templates
PROMPTS_BUCKET=scribbe-ai-dev-prompts
```

### Feature Flags
```bash
ENABLE_WEB_SEARCH=true               # Web search capabilities
ENABLE_DOCUMENT_KB=true              # Document knowledge base
ENABLE_FINANCIAL_DATA=false          # Financial data features
```

## 🛠️ Development Workflow

### Local Development
1. Edit `.env` file with your keys
2. Test locally (env variables auto-loaded)
3. Deploy when ready

### Production Deployment
```bash
# Method 1: Deploy script (recommended)
python scripts/deploy_with_env.py

# Method 2: Manual Lambda update
aws lambda update-function-configuration \
  --function-name scribbe-ai-dev-orchestrator \
  --environment Variables="{USE_LANGCHAIN=true,TAVILY_API_KEY=your-key}"
```

## 🧪 Testing Configuration

### Verify Environment Loading
```bash
# Check if .env is loaded correctly
python -c "
import sys
sys.path.append('application/backend/orchestrator')
from env_loader import load_env_file
load_env_file()
import os
print('LangChain enabled:', os.getenv('USE_LANGCHAIN'))
print('Tavily configured:', bool(os.getenv('TAVILY_API_KEY')))
"
```

### Test LangChain Orchestrator
```bash
# Enable LangChain and test
curl -X POST https://your-api-url/presentations \
  -H "Content-Type: application/json" \
  -d '{"instructions": "Search for latest AI news", "use_langchain": true}'
```

## 🎯 Examples

### Basic Configuration
```bash
USE_LANGCHAIN=true
TAVILY_API_KEY=tvly-abc123
ENABLE_WEB_SEARCH=true
```

### Full Configuration
```bash
# Core
USE_LANGCHAIN=true
ENVIRONMENT=dev
AWS_REGION=eu-west-1

# API Keys
TAVILY_API_KEY=tvly-abc123
SERPAPI_API_KEY=xyz789

# Features
ENABLE_WEB_SEARCH=true
ENABLE_DOCUMENT_KB=true
ENABLE_FINANCIAL_DATA=false

# Buckets
OUTPUT_BUCKET=scribbe-ai-dev-output
DOCUMENTS_BUCKET=scribbe-ai-dev-documents
```

## ❓ Troubleshooting

### Environment Not Loading
```bash
# Check if .env file exists
ls -la .env

# Verify env_loader works
python application/backend/orchestrator/env_loader.py
```

### API Keys Not Working
1. Verify keys are correct in `.env`
2. Check for extra spaces or quotes
3. Ensure keys are active on provider websites
4. Deploy updated configuration to Lambda

### Lambda Not Updated
```bash
# Re-run deployment script
python scripts/deploy_with_env.py

# Or manually update via AWS CLI
aws lambda get-function-configuration \
  --function-name scribbe-ai-dev-orchestrator \
  --query 'Environment.Variables'
```

## 🔐 Best Practices

1. **Never commit .env files** - They contain secrets
2. **Use strong API keys** - Rotate regularly  
3. **Monitor usage** - Track API costs
4. **Test before deploy** - Verify locally first
5. **Document changes** - Update .env.example when adding new variables

## 📞 Support

For configuration issues:
1. Check this documentation
2. Verify .env.example template
3. Review CloudWatch logs
4. Contact development team