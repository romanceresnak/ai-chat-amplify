# Cognito User Pool
resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-${var.environment}-user-pool"

  # Username configuration
  username_attributes      = var.username_attributes
  auto_verified_attributes = var.auto_verified_attributes

  # Password policy
  password_policy {
    minimum_length                   = var.password_policy.minimum_length
    require_lowercase                = var.password_policy.require_lowercase
    require_numbers                  = var.password_policy.require_numbers
    require_symbols                  = var.password_policy.require_symbols
    require_uppercase                = var.password_policy.require_uppercase
    temporary_password_validity_days = var.password_policy.temporary_password_validity_days
  }

  # MFA configuration
  mfa_configuration = var.mfa_configuration

  software_token_mfa_configuration {
    enabled = var.mfa_configuration != "OFF"
  }

  # Email configuration
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }

  # Account recovery
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # User attribute schema
  schema {
    attribute_data_type = "String"
    name                = "email"
    required            = true
    mutable             = true

    string_attribute_constraints {
      min_length = 0
      max_length = 2048
    }
  }

  # Verification message template
  verification_message_template {
    default_email_option = "CONFIRM_WITH_CODE"
    email_subject        = "Overte svoj účet pre ${var.project_name}"
    email_message        = "Váš overovací kód je {####}"
  }

  # User pool add-ons
  user_pool_add_ons {
    advanced_security_mode = "OFF"
  }

  # Device configuration
  device_configuration {
    challenge_required_on_new_device      = false
    device_only_remembered_on_user_prompt = false
  }

  tags = var.tags
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.project_name}-${var.environment}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  # Token validity
  refresh_token_validity = 30
  access_token_validity  = 60
  id_token_validity      = 60

  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "days"
  }

  # Auth flows
  explicit_auth_flows = [
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_PASSWORD_AUTH"
  ]

  # OAuth
  supported_identity_providers = ["COGNITO"]
  
  # Prevent user existence errors
  prevent_user_existence_errors = "ENABLED"

  # Read/write attributes
  read_attributes = [
    "email",
    "email_verified",
    "preferred_username",
    "profile",
    "updated_at"
  ]

  write_attributes = [
    "email",
    "preferred_username",
    "profile",
    "updated_at"
  ]

  generate_secret = false
}

# Cognito Identity Pool
resource "aws_cognito_identity_pool" "main" {
  identity_pool_name               = "${var.project_name}-${var.environment}-identity-pool"
  allow_unauthenticated_identities = false
  allow_classic_flow               = false

  cognito_identity_providers {
    client_id     = aws_cognito_user_pool_client.main.id
    provider_name = aws_cognito_user_pool.main.endpoint
  }

  tags = var.tags
}

# IAM role for authenticated users
resource "aws_iam_role" "authenticated" {
  name = "${var.project_name}-${var.environment}-cognito-authenticated"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.main.id
          }
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "authenticated"
          }
        }
      }
    ]
  })

  tags = var.tags
}

# IAM role for unauthenticated users (minimal permissions)
resource "aws_iam_role" "unauthenticated" {
  name = "${var.project_name}-${var.environment}-cognito-unauthenticated"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Federated = "cognito-identity.amazonaws.com"
        }
        Action = "sts:AssumeRoleWithWebIdentity"
        Condition = {
          StringEquals = {
            "cognito-identity.amazonaws.com:aud" = aws_cognito_identity_pool.main.id
          }
          "ForAnyValue:StringLike" = {
            "cognito-identity.amazonaws.com:amr" = "unauthenticated"
          }
        }
      }
    ]
  })

  tags = var.tags
}

# Policy for authenticated users - Bedrock access
resource "aws_iam_role_policy" "authenticated_bedrock" {
  name = "bedrock-access"
  role = aws_iam_role.authenticated.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:*:*:inference-profile/*",
          "arn:aws:bedrock:*::foundation-model/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:Retrieve",
          "bedrock:RetrieveAndGenerate"
        ]
        Resource = "*"
      }
    ]
  })
}

# Policy for authenticated users - S3 access
resource "aws_iam_role_policy" "authenticated_s3" {
  name = "s3-access"
  role = aws_iam_role.authenticated.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:DeleteObject"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_name}-${var.environment}-storage/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::${var.project_name}-${var.environment}-storage"
        ]
        Condition = {
          StringLike = {
            "s3:prefix" = [
              "public/*",
              "protected/$${cognito-identity.amazonaws.com:sub}/*",
              "private/$${cognito-identity.amazonaws.com:sub}/*"
            ]
          }
        }
      }
    ]
  })
}

# Cognito Identity Pool Role Attachment
resource "aws_cognito_identity_pool_roles_attachment" "main" {
  identity_pool_id = aws_cognito_identity_pool.main.id

  roles = {
    "authenticated"   = aws_iam_role.authenticated.arn
    "unauthenticated" = aws_iam_role.unauthenticated.arn
  }

  role_mapping {
    identity_provider         = "${aws_cognito_user_pool.main.endpoint}:${aws_cognito_user_pool_client.main.id}"
    ambiguous_role_resolution = "AuthenticatedRole"
    type                      = "Token"
  }
}

# S3 bucket pre chat súbory
resource "aws_s3_bucket" "storage" {
  bucket = "${var.project_name}-${var.environment}-storage"
  tags   = var.tags
}

resource "aws_s3_bucket_cors_configuration" "storage" {
  bucket = aws_s3_bucket.storage.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["GET", "HEAD", "PUT", "POST", "DELETE"]
    allowed_origins = ["*"]
    expose_headers  = [
      "x-amz-server-side-encryption",
      "x-amz-request-id",
      "x-amz-id-2",
      "ETag"
    ]
    max_age_seconds = 3000
  }
}

resource "aws_s3_bucket_public_access_block" "storage" {
  bucket = aws_s3_bucket.storage.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}