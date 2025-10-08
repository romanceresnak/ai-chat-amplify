#!/usr/bin/env python3
"""
Deploy script that reads .env file and applies environment variables to AWS Lambda
"""
import os
import sys
import boto3
import json
from pathlib import Path

def load_env_file():
    """Load environment variables from .env file"""
    env_file = Path(__file__).parent.parent / '.env'
    
    if not env_file.exists():
        print(f"❌ .env file not found at: {env_file}")
        print("📝 Create .env file from .env.example template")
        return {}
    
    env_vars = {}
    with open(env_file, 'r') as file:
        for line in file:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip().strip('"\'')
    
    return env_vars

def update_lambda_env(function_name, env_vars):
    """Update Lambda function environment variables"""
    try:
        lambda_client = boto3.client('lambda', region_name='eu-west-1')
        
        # Get current function configuration
        response = lambda_client.get_function_configuration(FunctionName=function_name)
        current_env = response.get('Environment', {}).get('Variables', {})
        
        # Merge with new environment variables
        updated_env = {**current_env, **env_vars}
        
        # Update function
        lambda_client.update_function_configuration(
            FunctionName=function_name,
            Environment={
                'Variables': updated_env
            }
        )
        
        print(f"✅ Updated {function_name} with {len(env_vars)} environment variables")
        
        # Print what was updated (hide sensitive keys)
        for key, value in env_vars.items():
            if any(secret in key.lower() for secret in ['key', 'secret', 'password', 'token']):
                print(f"   {key}: {'*' * len(value)}")
            else:
                print(f"   {key}: {value}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error updating {function_name}: {str(e)}")
        return False

def main():
    """Main deployment function"""
    print("🚀 Deploying Lambda with environment variables from .env file")
    
    # Load environment variables
    env_vars = load_env_file()
    if not env_vars:
        sys.exit(1)
    
    # Function name
    function_name = "scribbe-ai-dev-orchestrator"
    
    # Update Lambda function
    success = update_lambda_env(function_name, env_vars)
    
    if success:
        print(f"\n🎉 Successfully deployed {function_name} with environment variables!")
        print("\n📝 Next steps:")
        print("1. Test the LangChain orchestrator")
        print("2. Add your actual API keys to .env file")
        print("3. Re-run this script to update Lambda")
    else:
        print("\n❌ Deployment failed")
        sys.exit(1)

if __name__ == "__main__":
    main()