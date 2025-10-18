environment    = "dev"
aws_region     = "us-east-1"
owner          = "development-team"
retention_days = 7

vpc_cidr           = "10.0.0.0/16"
availability_zones = ["us-east-1a", "us-east-1b"]
enable_nat_gateway = false

# Project configuration
project_name = "financepres-maker"

# Amplify Hosting configuration
repository_url  = "https://github.com/neil77450/financepresentationmaker"
git_branch      = "main"
custom_domain   = ""  # Optional: "yourdomain.com"
github_token    = "YOUR_GITHUB_TOKEN_HERE"  # Set this via environment variable or Terraform Cloud