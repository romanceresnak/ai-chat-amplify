variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "scribbe-ai"
}

variable "lambda_role_arn" {
  description = "IAM role ARN for Lambda functions"
  type        = string
}

variable "bedrock_kb_id" {
  description = "Bedrock Knowledge Base ID"
  type        = string
}

variable "s3_buckets" {
  description = "Map of S3 bucket names"
  type = object({
    documents = string
    templates = string
    financial = string
    output    = string
    prompts   = string
  })
}

variable "vpc_config" {
  description = "VPC configuration for Lambda functions"
  type = object({
    subnet_ids         = list(string)
    security_group_ids = list(string)
  })
  default = null
}