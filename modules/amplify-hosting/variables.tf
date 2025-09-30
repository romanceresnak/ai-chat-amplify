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

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}