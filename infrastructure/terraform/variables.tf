# ============================================================================
# BCG DevOps GenAI POC - Terraform Variables (Simple Public Setup)
# ============================================================================

variable "project_name" {
  description = "Project name used for resource naming"
  type        = string
  default     = "bcg-devops-genai"
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
  default     = "poc"
}

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "aws_profile" {
  description = "AWS CLI profile to use"
  type        = string
  default     = "credit"
}

# Bedrock Configuration - Nova Pro
variable "bedrock_model_id" {
  description = "Bedrock foundation model ID"
  type        = string
  default     = "amazon.nova-pro-v1:0"
}

# GitHub Configuration
variable "github_token" {
  description = "GitHub Personal Access Token"
  type        = string
  sensitive   = true
  default     = ""
}

variable "github_repo" {
  description = "GitHub repository for agent access"
  type        = string
  default     = "i2k2-networks/ai-work-flow"
}

# Lambda Configuration
variable "lambda_runtime" {
  description = "Lambda runtime"
  type        = string
  default     = "python3.12"
}

variable "lambda_memory_size" {
  description = "Lambda memory size in MB"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Lambda timeout in seconds"
  type        = number
  default     = 60
}

# Tags
variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    Project     = "BCG-DevOps-GenAI"
    ManagedBy   = "Terraform"
    Environment = "poc"
    Owner       = "i2k2"
    Customer    = "BCG"
  }
}
