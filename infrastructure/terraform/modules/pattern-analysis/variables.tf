variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "scribbe-ai"
}

variable "knowledge_base_id" {
  description = "Bedrock Knowledge Base ID for pattern analysis"
  type        = string
}