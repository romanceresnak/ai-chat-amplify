variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "scribbe-ai"
}

variable "retention_days" {
  description = "Days to retain output files"
  type        = number
  default     = 30
}