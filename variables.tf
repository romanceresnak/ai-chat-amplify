variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "scribbe-ai"
}

variable "owner" {
  description = "Owner of the infrastructure"
  type        = string
}

variable "retention_days" {
  description = "Days to retain output files"
  type        = number
  default     = 30
}

variable "bedrock_model_arns" {
  description = "List of Bedrock model ARNs to use"
  type        = list(string)
  default = [
    "arn:aws:bedrock:*::foundation-model/eu.anthropic.claude-3-5-sonnet-20240620-v1:0",
    "arn:aws:bedrock:*::foundation-model/eu.anthropic.claude-3-sonnet-20240229-v1:0",
    "arn:aws:bedrock:*::foundation-model/cohere.embed-english-v3"
  ]
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["eu-west-1a", "eu-west-1b"]
}

variable "enable_nat_gateway" {
  description = "Should be true to provision NAT Gateways for each of your private networks"
  type        = bool
  default     = false
}

# Amplify Hosting variables
variable "repository_url" {
  description = "Git repository URL for Amplify hosting"
  type        = string
  default     = ""
}

variable "git_branch" {
  description = "Git branch to deploy"
  type        = string
  default     = "main"
}

variable "custom_domain" {
  description = "Custom domain for the Amplify app (optional)"
  type        = string
  default     = ""
}