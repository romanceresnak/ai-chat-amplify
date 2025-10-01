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
    appRoot: ai-chat-amplify/ai-chat-amplify
    frontend:
      phases:
        preBuild:
          commands:
            - npm --version
            - node --version
            - npm ci
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: .next
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
    NEXT_PUBLIC_BEDROCK_REGION      = "us-east-1"
  }

  # Custom rules for Next.js SSR routing
  custom_rule {
    source = "/_next/static/<*>"
    target = "/_next/static/<*>"
    status = "200"
  }

  custom_rule {
    source = "/_next/image/<*>"
    target = "/_next/image/<*>"
    status = "200"
  }

  custom_rule {
    source = "/favicon.ico"
    target = "/favicon.ico"
    status = "200"
  }

  custom_rule {
    source = "/<*>"
    target = "/<*>"
    status = "200"
  }

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
    AMPLIFY_MONOREPO_APP_ROOT = "ai-chat-amplify/ai-chat-amplify"
    _CUSTOM_IMAGE = "public.ecr.aws/docker/library/node:20"
    NEXT_PUBLIC_USER_POOL_ID        = var.cognito_user_pool_id
    NEXT_PUBLIC_USER_POOL_CLIENT_ID = var.cognito_user_pool_client_id
    NEXT_PUBLIC_IDENTITY_POOL_ID    = var.cognito_identity_pool_id
    NEXT_PUBLIC_AWS_REGION          = var.aws_region
    NEXT_PUBLIC_STORAGE_BUCKET      = var.storage_bucket_name
    NEXT_PUBLIC_BEDROCK_REGION      = "us-east-1"
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