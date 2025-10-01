#!/bin/bash

# Create trust policy for Amplify
cat > /tmp/amplify-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "amplify.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the IAM role
aws iam create-role \
  --role-name AmplifyServiceRole-Manual \
  --assume-role-policy-document file:///tmp/amplify-trust-policy.json \
  --description "Service role for AWS Amplify"

# Attach the Amplify managed policy
aws iam attach-role-policy \
  --role-name AmplifyServiceRole-Manual \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess-Amplify

echo "Role created successfully!"
echo "Role ARN: $(aws iam get-role --role-name AmplifyServiceRole-Manual --query 'Role.Arn' --output text)"