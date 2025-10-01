output "user_pool_id" {
  description = "The ID of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.id
}

output "user_pool_arn" {
  description = "The ARN of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.arn
}

output "user_pool_endpoint" {
  description = "The endpoint of the Cognito User Pool"
  value       = aws_cognito_user_pool.main.endpoint
}

output "user_pool_client_id" {
  description = "The ID of the Cognito User Pool Client"
  value       = aws_cognito_user_pool_client.main.id
}

output "identity_pool_id" {
  description = "The ID of the Cognito Identity Pool"
  value       = aws_cognito_identity_pool.main.id
}

output "authenticated_role_arn" {
  description = "The ARN of the authenticated IAM role"
  value       = aws_iam_role.authenticated.arn
}

output "unauthenticated_role_arn" {
  description = "The ARN of the unauthenticated IAM role"
  value       = aws_iam_role.unauthenticated.arn
}

output "storage_bucket_name" {
  description = "The name of the S3 storage bucket"
  value       = aws_s3_bucket.storage.id
}

output "storage_bucket_arn" {
  description = "The ARN of the S3 storage bucket"
  value       = aws_s3_bucket.storage.arn
}

output "aws_region" {
  description = "AWS region where resources are created"
  value       = data.aws_region.current.name
}

# Data source pre získanie regiónu
data "aws_region" "current" {}