# ============================================================================
# BCG DevOps GenAI POC - Full Terraform Configuration
# Includes: Bedrock Agent, Lambda Functions, DynamoDB, S3 Knowledge Base
# NO DevOps Guru/Inspector (cost saving)
# ============================================================================

terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.30"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }
}

provider "aws" {
  region  = var.aws_region
  profile = var.aws_profile

  default_tags {
    tags = var.tags
  }
}

# Random suffix for unique naming
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

locals {
  name_prefix = "${var.project_name}-${var.environment}"
  account_id  = data.aws_caller_identity.current.account_id
}

# ============================================================================
# Data Sources
# ============================================================================

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

# ============================================================================
# S3 Bucket for Knowledge Base (Templates, Policies, Runbooks)
# ============================================================================

resource "aws_s3_bucket" "knowledge_base" {
  bucket = "${local.name_prefix}-knowledge-base-${random_string.suffix.result}"
}

resource "aws_s3_bucket_versioning" "knowledge_base" {
  bucket = aws_s3_bucket.knowledge_base.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "knowledge_base" {
  bucket = aws_s3_bucket.knowledge_base.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Upload templates to S3
resource "aws_s3_object" "nodejs_template" {
  bucket = aws_s3_bucket.knowledge_base.id
  key    = "templates/github-actions/nodejs.yml"
  source = "${path.module}/../../templates/github-actions/nodejs.yml"
  etag   = filemd5("${path.module}/../../templates/github-actions/nodejs.yml")
}

resource "aws_s3_object" "python_template" {
  bucket = aws_s3_bucket.knowledge_base.id
  key    = "templates/github-actions/python.yml"
  source = "${path.module}/../../templates/github-actions/python.yml"
  etag   = filemd5("${path.module}/../../templates/github-actions/python.yml")
}

resource "aws_s3_object" "golang_template" {
  bucket = aws_s3_bucket.knowledge_base.id
  key    = "templates/github-actions/golang.yml"
  source = "${path.module}/../../templates/github-actions/golang.yml"
  etag   = filemd5("${path.module}/../../templates/github-actions/golang.yml")
}

resource "aws_s3_object" "java_template" {
  bucket = aws_s3_bucket.knowledge_base.id
  key    = "templates/github-actions/java.yml"
  source = "${path.module}/../../templates/github-actions/java.yml"
  etag   = filemd5("${path.module}/../../templates/github-actions/java.yml")
}

resource "aws_s3_object" "dotnet_template" {
  bucket = aws_s3_bucket.knowledge_base.id
  key    = "templates/github-actions/dotnet.yml"
  source = "${path.module}/../../templates/github-actions/dotnet.yml"
  etag   = filemd5("${path.module}/../../templates/github-actions/dotnet.yml")
}

resource "aws_s3_object" "security_policy" {
  bucket = aws_s3_bucket.knowledge_base.id
  key    = "policies/security-policy.md"
  source = "${path.module}/../../templates/policies/security-policy.md"
  etag   = filemd5("${path.module}/../../templates/policies/security-policy.md")
}

# ============================================================================
# DynamoDB Tables
# ============================================================================

# Audit Trail Table
resource "aws_dynamodb_table" "audit_trail" {
  name         = "${local.name_prefix}-audit-trail"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"
  range_key    = "timestamp"

  attribute {
    name = "session_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "action_type"
    type = "S"
  }

  global_secondary_index {
    name            = "action-type-index"
    hash_key        = "action_type"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name = "${local.name_prefix}-audit-trail"
  }
}

# Session State Table
resource "aws_dynamodb_table" "sessions" {
  name         = "${local.name_prefix}-sessions"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "session_id"

  attribute {
    name = "session_id"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name = "${local.name_prefix}-sessions"
  }
}

# ============================================================================
# IAM Role for Lambda Functions
# ============================================================================

resource "aws_iam_role" "lambda_role" {
  name = "${local.name_prefix}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# Lambda Basic Execution
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Bedrock Access Policy
resource "aws_iam_role_policy" "bedrock_access" {
  name = "${local.name_prefix}-bedrock-access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/*"
        ]
      }
    ]
  })
}

# DynamoDB Access Policy
resource "aws_iam_role_policy" "dynamodb_access" {
  name = "${local.name_prefix}-dynamodb-access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.audit_trail.arn,
          "${aws_dynamodb_table.audit_trail.arn}/index/*",
          aws_dynamodb_table.sessions.arn
        ]
      }
    ]
  })
}

# S3 Access Policy
resource "aws_iam_role_policy" "s3_access" {
  name = "${local.name_prefix}-s3-access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.knowledge_base.arn,
          "${aws_s3_bucket.knowledge_base.arn}/*"
        ]
      }
    ]
  })
}

# Secrets Manager Access (for GitHub token)
resource "aws_iam_role_policy" "secrets_access" {
  name = "${local.name_prefix}-secrets-access"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${local.account_id}:secret:${local.name_prefix}/*"
        ]
      }
    ]
  })
}

# ============================================================================
# Lambda Functions
# ============================================================================

# Workflow Generator Lambda
data "archive_file" "workflow_generator_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/workflow-generator"
  output_path = "${path.module}/workflow_generator.zip"
}

resource "aws_lambda_function" "workflow_generator" {
  filename         = data.archive_file.workflow_generator_zip.output_path
  function_name    = "${local.name_prefix}-workflow-generator"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  source_code_hash = data.archive_file.workflow_generator_zip.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size

  environment {
    variables = {
      BEDROCK_MODEL_ID = var.bedrock_model_id
      ENVIRONMENT      = var.environment
      AUDIT_TABLE      = aws_dynamodb_table.audit_trail.name
      KB_BUCKET        = aws_s3_bucket.knowledge_base.id
    }
  }
}

# GitHub Integration Lambda
data "archive_file" "github_integration_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/github-integration"
  output_path = "${path.module}/github_integration.zip"
}

resource "aws_lambda_function" "github_integration" {
  filename         = data.archive_file.github_integration_zip.output_path
  function_name    = "${local.name_prefix}-github-integration"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  source_code_hash = data.archive_file.github_integration_zip.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = 300 # 5 minutes for autonomous agent operations
  memory_size      = 256

  environment {
    variables = {
      GITHUB_SECRET_NAME = "${local.name_prefix}/github-token"
      ENVIRONMENT        = var.environment
      AUDIT_TABLE        = aws_dynamodb_table.audit_trail.name
    }
  }
}

# Security Scanner Lambda
data "archive_file" "security_scanner_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../lambda/security-scanner"
  output_path = "${path.module}/security_scanner.zip"
}

resource "aws_lambda_function" "security_scanner" {
  filename         = data.archive_file.security_scanner_zip.output_path
  function_name    = "${local.name_prefix}-security-scanner"
  role             = aws_iam_role.lambda_role.arn
  handler          = "index.handler"
  source_code_hash = data.archive_file.security_scanner_zip.output_base64sha256
  runtime          = var.lambda_runtime
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      ENVIRONMENT = var.environment
      AUDIT_TABLE = aws_dynamodb_table.audit_trail.name
    }
  }
}

# ============================================================================
# API Gateway (HTTP API)
# ============================================================================

resource "aws_apigatewayv2_api" "main" {
  name          = "${local.name_prefix}-api"
  protocol_type = "HTTP"

  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["Content-Type", "Authorization", "X-Amz-Date", "X-Api-Key"]
    max_age       = 300
  }
}

resource "aws_apigatewayv2_stage" "prod" {
  api_id      = aws_apigatewayv2_api.main.id
  name        = "prod"
  auto_deploy = true

  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_logs.arn
    format = jsonencode({
      requestId        = "$context.requestId"
      ip               = "$context.identity.sourceIp"
      requestTime      = "$context.requestTime"
      httpMethod       = "$context.httpMethod"
      routeKey         = "$context.routeKey"
      status           = "$context.status"
      responseLength   = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
    })
  }
}

# Lambda Integrations
resource "aws_apigatewayv2_integration" "workflow_generator" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.workflow_generator.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 29000 # Max allowed by API Gateway HTTP API
}

resource "aws_apigatewayv2_integration" "github_integration" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.github_integration.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 29000 # Max allowed by API Gateway HTTP API
}

resource "aws_apigatewayv2_integration" "security_scanner" {
  api_id                 = aws_apigatewayv2_api.main.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.security_scanner.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  timeout_milliseconds   = 29000 # Max allowed by API Gateway HTTP API
}

# Routes
resource "aws_apigatewayv2_route" "generate" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /generate"
  target    = "integrations/${aws_apigatewayv2_integration.workflow_generator.id}"
}

resource "aws_apigatewayv2_route" "health" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "GET /health"
  target    = "integrations/${aws_apigatewayv2_integration.workflow_generator.id}"
}

resource "aws_apigatewayv2_route" "analyze" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /analyze"
  target    = "integrations/${aws_apigatewayv2_integration.github_integration.id}"
}

resource "aws_apigatewayv2_route" "create_pr" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /create-pr"
  target    = "integrations/${aws_apigatewayv2_integration.github_integration.id}"
}

resource "aws_apigatewayv2_route" "scan" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /scan"
  target    = "integrations/${aws_apigatewayv2_integration.security_scanner.id}"
}

# Intelligent Agent Routes
resource "aws_apigatewayv2_route" "knowledge" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /knowledge"
  target    = "integrations/${aws_apigatewayv2_integration.github_integration.id}"
}

resource "aws_apigatewayv2_route" "track" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /track"
  target    = "integrations/${aws_apigatewayv2_integration.github_integration.id}"
}

resource "aws_apigatewayv2_route" "suggest" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /suggest"
  target    = "integrations/${aws_apigatewayv2_integration.github_integration.id}"
}

resource "aws_apigatewayv2_route" "fix" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /fix"
  target    = "integrations/${aws_apigatewayv2_integration.github_integration.id}"
}

resource "aws_apigatewayv2_route" "deploy" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /deploy"
  target    = "integrations/${aws_apigatewayv2_integration.github_integration.id}"
}

resource "aws_apigatewayv2_route" "validate" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /validate"
  target    = "integrations/${aws_apigatewayv2_integration.github_integration.id}"
}

# Autonomous Agent Route (fully autonomous DevOps agent)
resource "aws_apigatewayv2_route" "autonomous" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /autonomous"
  target    = "integrations/${aws_apigatewayv2_integration.github_integration.id}"
}

# Multi-Agent Coordination Route
resource "aws_apigatewayv2_route" "coordinate" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /coordinate"
  target    = "integrations/${aws_apigatewayv2_integration.github_integration.id}"
}

# Incident Response Route - Uses workflow_generator Lambda
resource "aws_apigatewayv2_route" "incident" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /incident"
  target    = "integrations/${aws_apigatewayv2_integration.workflow_generator.id}"
}

# Security Remediation Route - Prisma/SonarQube fix suggestions
resource "aws_apigatewayv2_route" "security_remediate" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /security-remediate"
  target    = "integrations/${aws_apigatewayv2_integration.workflow_generator.id}"
}

# RCA Report Generator Route
resource "aws_apigatewayv2_route" "rca" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /rca"
  target    = "integrations/${aws_apigatewayv2_integration.workflow_generator.id}"
}

# ArgoCD Manifest Generator Route
resource "aws_apigatewayv2_route" "argocd_manifest" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /argocd-manifest"
  target    = "integrations/${aws_apigatewayv2_integration.workflow_generator.id}"
}

# Reusable Workflow Generator Route
resource "aws_apigatewayv2_route" "reusable_workflow" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /reusable-workflow"
  target    = "integrations/${aws_apigatewayv2_integration.workflow_generator.id}"
}

# Autonomous Pipeline Generation Route (single-command full pipeline creation)
resource "aws_apigatewayv2_route" "pipeline" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /pipeline"
  target    = "integrations/${aws_apigatewayv2_integration.github_integration.id}"
}

resource "aws_apigatewayv2_route" "chat" {
  api_id    = aws_apigatewayv2_api.main.id
  route_key = "POST /chat"
  target    = "integrations/${aws_apigatewayv2_integration.github_integration.id}"
}

# Lambda Permissions for API Gateway
resource "aws_lambda_permission" "workflow_generator_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.workflow_generator.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "github_integration_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.github_integration.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

resource "aws_lambda_permission" "security_scanner_api" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.security_scanner.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.main.execution_arn}/*/*"
}

# ============================================================================
# Bedrock Agent IAM Role
# ============================================================================

resource "aws_iam_role" "bedrock_agent_role" {
  name = "${local.name_prefix}-bedrock-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = "sts:AssumeRole"
        Condition = {
          StringEquals = {
            "aws:SourceAccount" = local.account_id
          }
        }
      }
    ]
  })
}

resource "aws_iam_role_policy" "bedrock_agent_policy" {
  name = "${local.name_prefix}-bedrock-agent-policy"
  role = aws_iam_role.bedrock_agent_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.workflow_generator.arn,
          aws_lambda_function.github_integration.arn,
          aws_lambda_function.security_scanner.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.knowledge_base.arn,
          "${aws_s3_bucket.knowledge_base.arn}/*"
        ]
      }
    ]
  })
}

# Lambda permissions for Bedrock Agent
resource "aws_lambda_permission" "bedrock_workflow_generator" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.workflow_generator.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = "arn:aws:bedrock:${var.aws_region}:${local.account_id}:agent/*"
}

resource "aws_lambda_permission" "bedrock_github_integration" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.github_integration.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = "arn:aws:bedrock:${var.aws_region}:${local.account_id}:agent/*"
}

resource "aws_lambda_permission" "bedrock_security_scanner" {
  statement_id  = "AllowBedrockAgentInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.security_scanner.function_name
  principal     = "bedrock.amazonaws.com"
  source_arn    = "arn:aws:bedrock:${var.aws_region}:${local.account_id}:agent/*"
}

# ============================================================================
# CloudWatch Logs
# ============================================================================

resource "aws_cloudwatch_log_group" "workflow_generator_logs" {
  name              = "/aws/lambda/${local.name_prefix}-workflow-generator"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "github_integration_logs" {
  name              = "/aws/lambda/${local.name_prefix}-github-integration"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "security_scanner_logs" {
  name              = "/aws/lambda/${local.name_prefix}-security-scanner"
  retention_in_days = 7
}

resource "aws_cloudwatch_log_group" "api_logs" {
  name              = "/aws/apigateway/${local.name_prefix}-api"
  retention_in_days = 7
}

# ============================================================================
# Outputs
# ============================================================================

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "${aws_apigatewayv2_api.main.api_endpoint}/prod"
}

output "endpoints" {
  description = "All API endpoints"
  value = {
    health     = "${aws_apigatewayv2_api.main.api_endpoint}/prod/health"
    generate   = "${aws_apigatewayv2_api.main.api_endpoint}/prod/generate"
    analyze    = "${aws_apigatewayv2_api.main.api_endpoint}/prod/analyze"
    create_pr  = "${aws_apigatewayv2_api.main.api_endpoint}/prod/create-pr"
    scan       = "${aws_apigatewayv2_api.main.api_endpoint}/prod/scan"
    knowledge  = "${aws_apigatewayv2_api.main.api_endpoint}/prod/knowledge"
    track      = "${aws_apigatewayv2_api.main.api_endpoint}/prod/track"
    suggest    = "${aws_apigatewayv2_api.main.api_endpoint}/prod/suggest"
    fix        = "${aws_apigatewayv2_api.main.api_endpoint}/prod/fix"
    deploy     = "${aws_apigatewayv2_api.main.api_endpoint}/prod/deploy"
    validate   = "${aws_apigatewayv2_api.main.api_endpoint}/prod/validate"
    autonomous = "${aws_apigatewayv2_api.main.api_endpoint}/prod/autonomous"
    pipeline   = "${aws_apigatewayv2_api.main.api_endpoint}/prod/pipeline"
  }
}

output "lambda_functions" {
  description = "Lambda function names"
  value = {
    workflow_generator = aws_lambda_function.workflow_generator.function_name
    github_integration = aws_lambda_function.github_integration.function_name
    security_scanner   = aws_lambda_function.security_scanner.function_name
  }
}

output "knowledge_base_bucket" {
  description = "S3 bucket for knowledge base"
  value       = aws_s3_bucket.knowledge_base.id
}

output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = {
    audit_trail = aws_dynamodb_table.audit_trail.name
    sessions    = aws_dynamodb_table.sessions.name
  }
}

output "bedrock_agent_role_arn" {
  description = "IAM Role ARN for Bedrock Agent"
  value       = aws_iam_role.bedrock_agent_role.arn
}

output "account_id" {
  description = "AWS Account ID"
  value       = data.aws_caller_identity.current.account_id
}

output "github_secret_name" {
  description = "Name for GitHub token in Secrets Manager"
  value       = "${local.name_prefix}/github-token"
}
