variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment (dev, prod)"
  type        = string
}

variable "repository_url" {
  description = "Git repository URL"
  type        = string
  validation {
    condition     = length(var.repository_url) > 0 && length(var.repository_url) <= 1000
    error_message = "The repository_url must be between 1 and 1000 characters."
  }
}

variable "branch_name" {
  description = "Git branch to deploy"
  type        = string
  default     = "main"
}

variable "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  type        = string
}

variable "cognito_user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  type        = string
}

variable "cognito_identity_pool_id" {
  description = "Cognito Identity Pool ID"
  type        = string
}

variable "aws_region" {
  description = "AWS Region"
  type        = string
}

variable "storage_bucket_name" {
  description = "S3 Storage bucket name"
  type        = string
}

variable "custom_domain" {
  description = "Custom domain for the app (optional)"
  type        = string
  default     = ""
}

variable "github_token" {
  description = "GitHub OAuth token for repository access"
  type        = string
  sensitive   = true
  default     = ""
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "api_gateway_url" {
  description = "API Gateway URL for Lambda functions"
  type        = string
  default     = ""
}