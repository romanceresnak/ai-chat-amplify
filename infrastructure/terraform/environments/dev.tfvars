environment    = "dev"
aws_region     = "eu-west-1"
owner          = "development-team"
retention_days = 7

vpc_cidr           = "10.0.0.0/16"
availability_zones = ["eu-west-1a", "eu-west-1b"]
enable_nat_gateway = false

# Project configuration
project_name = "scribbe-ai"

# Amplify Hosting configuration
repository_url  = "https://github.com/romanceresnak/ai-chat-amplify"
git_branch      = "main"
custom_domain   = ""  # Optional: "yourdomain.com"
github_token    =  ""