terraform {
  required_version = ">= 1.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  backend "s3" {
    bucket = "scribbe-terraform-state"
    key    = "infrastructure/terraform.tfstate"
    region = "eu-west-1"
  }
}

provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = "ScribbeAI"
      ManagedBy   = "Terraform"
      Owner       = var.owner
    }
  }
}

# Networking
module "networking" {
  source = "./modules/networking"
  
  project_name       = var.project_name
  environment        = var.environment
  vpc_cidr          = var.vpc_cidr
  availability_zones = var.availability_zones
  enable_nat_gateway = var.enable_nat_gateway
}

# S3 Buckets
module "s3" {
  source = "./modules/s3"
  
  environment     = var.environment
  project_name    = var.project_name
  retention_days  = var.retention_days
}

# IAM Roles and Policies
module "iam" {
  source = "./modules/iam"
  
  environment         = var.environment
  project_name        = var.project_name
  s3_buckets         = module.s3.bucket_arns
  bedrock_model_arns = var.bedrock_model_arns
}

# Bedrock Configuration
module "bedrock" {
  source = "./modules/bedrock"
  
  environment           = var.environment
  project_name          = var.project_name
  knowledge_base_role   = module.iam.bedrock_kb_role_arn
  agent_role            = module.iam.bedrock_agent_role_arn
  s3_data_source_bucket = module.s3.documents_bucket_arn
}

# Lambda Functions
module "lambda_functions" {
  source = "./modules/lambda"
  
  environment          = var.environment
  project_name         = var.project_name
  lambda_role_arn      = module.iam.lambda_role_arn
  bedrock_kb_id        = module.bedrock.knowledge_base_id
  s3_buckets          = module.s3.bucket_names
  vpc_config = {
    subnet_ids         = module.networking.private_subnet_ids
    security_group_ids = [module.networking.lambda_security_group_id]
  }
}

# API Gateway
module "api_gateway" {
  source = "./modules/api-gateway"
  
  environment             = var.environment
  project_name            = var.project_name
  lambda_function_arns    = module.lambda_functions.function_arns
  lambda_invoke_arns      = module.lambda_functions.invoke_arns
}

# Cognito User Pool and Identity Pool
module "cognito" {
  source = "./modules/cognito"
  
  project_name = var.project_name
  environment  = var.environment
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}

# Amplify Hosting for frontend application
module "amplify_hosting" {
  source = "./modules/amplify-hosting"
  
  project_name                = var.project_name
  environment                 = var.environment
  repository_url              = var.repository_url
  branch_name                 = var.git_branch
  github_token                = var.github_token
  cognito_user_pool_id        = module.cognito.user_pool_id
  cognito_user_pool_client_id = module.cognito.user_pool_client_id
  cognito_identity_pool_id    = module.cognito.identity_pool_id
  aws_region                  = var.aws_region
  storage_bucket_name         = module.cognito.storage_bucket_name
  custom_domain              = var.custom_domain
  
  tags = {
    Environment = var.environment
    Project     = var.project_name
  }
}