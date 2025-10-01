variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "scribbe-ai"
}

variable "knowledge_base_role" {
  description = "IAM role ARN for Bedrock Knowledge Base"
  type        = string
}

variable "agent_role" {
  description = "IAM role ARN for Bedrock Agent"
  type        = string
}

variable "s3_data_source_bucket" {
  description = "S3 bucket ARN for documents data source"
  type        = string
}