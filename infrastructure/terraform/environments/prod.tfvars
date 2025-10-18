environment    = "prod"
aws_region     = "us-east-1"
owner          = "production-team"
retention_days = 30

vpc_cidr           = "10.1.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]
enable_nat_gateway = true

# Project configuration
project_name = "financepres-maker"

# Amplify Hosting configuration
repository_url  = "https://github.com/neil77450/financepresentationmaker"
git_branch      = "main"
custom_domain   = ""  # Optional: "yourdomain.com"
github_token    = ""  # Set this via environment variable TF_VAR_github_token