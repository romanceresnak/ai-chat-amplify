variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "scribbe-ai"
}

variable "s3_buckets" {
  description = "List of S3 bucket ARNs"
  type        = list(string)
}

variable "bedrock_model_arns" {
  description = "List of Bedrock model ARNs to use"
  type        = list(string)
  default = [
    "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-opus-20240229",
    "arn:aws:bedrock:*::foundation-model/anthropic.claude-3-sonnet-20240229",
    "arn:aws:bedrock:*::foundation-model/amazon.titan-embed-text-v1"
  ]
}