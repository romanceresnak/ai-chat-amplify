output "api_url" {
  description = "API Gateway endpoint URL"
  value       = module.api_gateway.api_url
}

output "bucket_names" {
  description = "S3 bucket names"
  value       = module.s3.bucket_names
}

output "knowledge_base_id" {
  description = "Bedrock Knowledge Base ID"
  value       = module.bedrock.knowledge_base_id
}

output "lambda_function_arns" {
  description = "Lambda function ARNs"
  value       = module.lambda_functions.function_arns
}

output "region" {
  description = "AWS region"
  value       = var.aws_region
}

output "environment" {
  description = "Environment name"
  value       = var.environment
}

# Cognito outputs
output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = module.cognito.user_pool_id
}

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = module.cognito.user_pool_client_id
}

output "cognito_identity_pool_id" {
  description = "Cognito Identity Pool ID"
  value       = module.cognito.identity_pool_id
}

output "cognito_user_pool_endpoint" {
  description = "Cognito User Pool endpoint"
  value       = module.cognito.user_pool_endpoint
}

output "cognito_storage_bucket" {
  description = "S3 bucket for chat file storage"
  value       = module.cognito.storage_bucket_name
}

# Amplify Hosting outputs
output "amplify_app_id" {
  description = "Amplify App ID"
  value       = module.amplify_hosting.app_id
}

output "amplify_app_url" {
  description = "Amplify app URL"
  value       = module.amplify_hosting.app_url
}

output "amplify_custom_domain_url" {
  description = "Custom domain URL if configured"
  value       = module.amplify_hosting.custom_domain_url
}