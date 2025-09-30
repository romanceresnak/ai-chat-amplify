variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "scribbe-ai"
}

variable "lambda_function_arns" {
  description = "Map of Lambda function ARNs"
  type = object({
    orchestrator       = string
    content_generator  = string
    template_processor = string
  })
}

variable "lambda_invoke_arns" {
  description = "Map of Lambda function invoke ARNs"
  type = object({
    orchestrator       = string
    content_generator  = string
    template_processor = string
  })
}