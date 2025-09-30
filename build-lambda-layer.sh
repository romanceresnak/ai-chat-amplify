#!/bin/bash

# Create a temporary directory for the layer
mkdir -p modules/lambda/layers/python

# Install dependencies using python -m pip
python3 -m pip install -r lambda-functions/requirements.txt -t modules/lambda/layers/python/

# Create the zip file
cd modules/lambda/layers
zip -r python-libs.zip python/

# Clean up
rm -rf python/

echo "Lambda layer created successfully!"