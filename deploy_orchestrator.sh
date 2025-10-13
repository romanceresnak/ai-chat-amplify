#!/bin/bash
# Deploy orchestrator Lambda function

set -e

echo "Deploying orchestrator Lambda..."

# Change to project directory
cd "$(dirname "$0")"

# Remove old zip if exists
rm -f infrastructure/terraform/modules/lambda/orchestrator.zip

# Create new zip
cd application/backend/orchestrator
zip -r ../../../infrastructure/terraform/modules/lambda/orchestrator.zip . -x "*.pyc" -x "__pycache__/*" -x "test_*"

cd ../../..

# Deploy using Terraform
cd infrastructure/terraform
terraform apply -auto-approve \
    -var-file="environments/dev.tfvars" \
    -target=module.lambda.data.archive_file.orchestrator \
    -target=module.lambda.aws_lambda_function.orchestrator

echo "Deployment complete!"