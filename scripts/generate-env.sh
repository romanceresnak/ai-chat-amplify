#!/bin/bash

# Script to generate .env file from Terraform outputs
# Usage: ./scripts/generate-env.sh

echo "Generating .env file from Terraform outputs..."

# Get Terraform outputs
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id 2>/dev/null)
USER_POOL_CLIENT_ID=$(terraform output -raw cognito_user_pool_client_id 2>/dev/null)
IDENTITY_POOL_ID=$(terraform output -raw cognito_identity_pool_id 2>/dev/null)
AWS_REGION=$(terraform output -raw region 2>/dev/null)
STORAGE_BUCKET=$(terraform output -raw cognito_storage_bucket 2>/dev/null)
AMPLIFY_APP_URL=$(terraform output -raw amplify_app_url 2>/dev/null)

# Create .env file
cat > ai-chat-amplify/ai-chat-amplify/.env.local << EOF
# AWS Cognito Configuration
NEXT_PUBLIC_USER_POOL_ID=$USER_POOL_ID
NEXT_PUBLIC_USER_POOL_CLIENT_ID=$USER_POOL_CLIENT_ID
NEXT_PUBLIC_IDENTITY_POOL_ID=$IDENTITY_POOL_ID
NEXT_PUBLIC_AWS_REGION=$AWS_REGION

# S3 Storage Configuration  
NEXT_PUBLIC_STORAGE_BUCKET=$STORAGE_BUCKET

# Bedrock Configuration
NEXT_PUBLIC_BEDROCK_REGION=us-east-1
EOF

echo "✅ .env.local file generated successfully!"
echo "📍 Location: ai-chat-amplify/ai-chat-amplify/.env.local"
echo ""
echo "🚀 Amplify App URL: $AMPLIFY_APP_URL"
echo "🔐 Cognito User Pool ID: $USER_POOL_ID"