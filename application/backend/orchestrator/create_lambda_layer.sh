#!/bin/bash

# Create Lambda layer for python-pptx and other dependencies

echo "Creating Lambda layer for orchestrator dependencies..."

# Create temporary directory
mkdir -p lambda-layer/python

# Install dependencies
pip install -r requirements.txt -t lambda-layer/python/

# Create zip file
cd lambda-layer
zip -r ../orchestrator-layer.zip .

# Clean up
cd ..
rm -rf lambda-layer

echo "Lambda layer created: orchestrator-layer.zip"
echo ""
echo "To deploy the layer to AWS:"
echo "aws lambda publish-layer-version \\"
echo "    --layer-name scribbe-ai-orchestrator-layer \\"
echo "    --description 'Python dependencies for orchestrator including python-pptx' \\"
echo "    --zip-file fileb://orchestrator-layer.zip \\"
echo "    --compatible-runtimes python3.11 \\"
echo "    --region eu-west-1"