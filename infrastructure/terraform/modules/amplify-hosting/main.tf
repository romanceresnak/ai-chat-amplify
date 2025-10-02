# Get current AWS account ID
data "aws_caller_identity" "current" {}

# Get current AWS region
data "aws_region" "current" {}


# Amplify Hosting for the Next.js app - automaticky sa pripojí k GitHub repository

resource "aws_amplify_app" "main" {
  count = var.repository_url != "" ? 1 : 0
  
  name = "${var.project_name}-${var.environment}-app-v2"
  
  # GitHub repository connection
  repository   = var.repository_url
  oauth_token  = var.github_token
  
  # No IAM service role - let Amplify handle it
  
  # Build settings for Next.js in subdirectory
  build_spec = <<-EOT
    version: 1
    frontend:
      phases:
        preBuild:
          commands:
            - npm ci
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: out
        files:
          - '**/*'
      cache:
        paths:
          - node_modules/**/*
  EOT

  # Environment variables from Cognito outputs
  environment_variables = {
    NEXT_PUBLIC_USER_POOL_ID        = var.cognito_user_pool_id
    NEXT_PUBLIC_USER_POOL_CLIENT_ID = var.cognito_user_pool_client_id
    NEXT_PUBLIC_IDENTITY_POOL_ID    = var.cognito_identity_pool_id
    NEXT_PUBLIC_AWS_REGION          = var.aws_region
    NEXT_PUBLIC_STORAGE_BUCKET      = var.storage_bucket_name
    NEXT_PUBLIC_BEDROCK_REGION      = var.aws_region
    NEXT_PUBLIC_API_URL             = var.api_gateway_url
  }

  # Custom rules for Next.js App - removed as they interfere with SSR

  # Auto branch creation
  enable_auto_branch_creation = true
  auto_branch_creation_patterns = ["main", "dev"]
  
  auto_branch_creation_config {
    enable_auto_build = true
  }

  tags = var.tags
}

# Branch deployment
resource "aws_amplify_branch" "main" {
  count = var.repository_url != "" ? 1 : 0
  
  app_id      = aws_amplify_app.main[0].id
  branch_name = var.branch_name
  
  framework = "Next.js - SSR"
  
  environment_variables = {
    AMPLIFY_DIFF_DEPLOY = "false"
    AMPLIFY_MONOREPO_APP_ROOT = "application/frontend"
    _CUSTOM_IMAGE = "public.ecr.aws/docker/library/node:20"
    NEXT_PUBLIC_USER_POOL_ID        = var.cognito_user_pool_id
    NEXT_PUBLIC_USER_POOL_CLIENT_ID = var.cognito_user_pool_client_id
    NEXT_PUBLIC_IDENTITY_POOL_ID    = var.cognito_identity_pool_id
    NEXT_PUBLIC_AWS_REGION          = var.aws_region
    NEXT_PUBLIC_STORAGE_BUCKET      = var.storage_bucket_name
    NEXT_PUBLIC_BEDROCK_REGION      = var.aws_region
    NEXT_PUBLIC_API_URL             = var.api_gateway_url
  }
}

# Domain association (optional)
resource "aws_amplify_domain_association" "main" {
  count = var.custom_domain != "" && var.repository_url != "" ? 1 : 0
  
  app_id      = aws_amplify_app.main[0].id
  domain_name = var.custom_domain

  sub_domain {
    branch_name = aws_amplify_branch.main[0].branch_name
    prefix      = ""
  }
}