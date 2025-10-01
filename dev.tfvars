# Development environment configuration
environment = "dev"
owner       = "development-team"

# Project configuration
project_name = "scribbe-ai"

# AWS configuration
aws_region = "eu-west-1"

# Networking configuration
vpc_cidr           = "10.0.0.0/16"
availability_zones = ["eu-west-1a", "eu-west-1b"]
enable_nat_gateway = false

# Data retention
retention_days = 30

# Bedrock model configuration
bedrock_model_arns = [
  "arn:aws:bedrock:*::foundation-model/eu.anthropic.claude-3-5-sonnet-20240620-v1:0",
  "arn:aws:bedrock:*::foundation-model/eu.anthropic.claude-3-sonnet-20240229-v1:0",
  "arn:aws:bedrock:*::foundation-model/cohere.embed-english-v3"
]

# Amplify Hosting configuration pre globálny deployment
repository_url  = "https://github.com/romanceresnak/ai-chat-amplify"
git_branch      = "main"
custom_domain   = ""  # Voliteľne: "yourdomain.com"
