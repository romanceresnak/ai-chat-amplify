#!/bin/bash

# Deploy ScribbeAI with AI Presentation Generator

set -e

echo "🚀 Deploying ScribbeAI with AI Presentation Generator..."
echo ""

# Check if we're in the correct directory
if [ ! -f "infrastructure/terraform/main.tf" ]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi

# Navigate to terraform directory
cd infrastructure/terraform

# Initialize Terraform
echo "📦 Initializing Terraform..."
terraform init

# Plan the deployment
echo "📋 Planning deployment..."
terraform plan -var-file=environments/dev.tfvars -out=tfplan

# Apply the deployment
echo "🏗️ Applying infrastructure changes..."
terraform apply tfplan

# Get outputs
echo ""
echo "✅ Deployment completed!"
echo ""
echo "📊 Important outputs:"
echo "-------------------"
terraform output -json | jq -r '
  "API Gateway URL: " + .api_gateway_url.value,
  "Orchestrator Lambda: " + .lambda_functions.value.orchestrator,
  "Lambda Layer ARN: " + .lambda_layer_arn.value
'

echo ""
echo "🎯 Next steps:"
echo "1. Test the AI presentation generator with:"
echo "   - 'Create a 40 page slide deck to present the merits of a deal to a private equity investment Committee'"
echo "   - 'Create a deck to present a debt issuance deal to potential buyers'"
echo "   - 'Create a professional corporate slide titled Loan Portfolio...'"
echo ""
echo "2. Monitor Lambda logs in CloudWatch for any issues"
echo "3. Check S3 output bucket for generated presentations"
echo ""
echo "💡 The AI generator will create unique presentations for each request!"