# Optional: Amplify Hosting for the Next.js app

resource "aws_amplify_app" "main" {
  count = var.repository_url != "" ? 1 : 0
  
  name       = "${var.project_name}-${var.environment}"
  repository = var.repository_url
  
  # Build settings for Next.js with subpath
  build_spec = <<-EOT
    version: 1
    applications:
      - appRoot: ai-chat-amplify/ai-chat-amplify
        frontend:
          phases:
            preBuild:
              commands:
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

  # Custom rules for Next.js SPA routing
  custom_rule {
    source = "/<*>"
    status = "404"
    target = "/index.html"
  }

  custom_rule {
    source = "</^[^.]+$|\.(?!(css|gif|ico|jpg|js|png|txt|svg|woff|ttf|map|json)$)([^.]+$)/>"
    status = "200"
    target = "/index.html"
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