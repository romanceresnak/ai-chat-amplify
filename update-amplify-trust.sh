#!/bin/bash

# Update trust relationship for existing role
aws iam update-assume-role-policy \
  --role-name AmplifyServiceRole-Manual \
  --policy-document file://fix-amplify-role.json

echo "Trust policy updated!"

# Verify the trust policy
echo -e "\nCurrent trust policy:"
aws iam get-role --role-name AmplifyServiceRole-Manual --query 'Role.AssumeRolePolicyDocument' --output json