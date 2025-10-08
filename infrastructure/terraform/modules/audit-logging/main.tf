# DynamoDB table for audit logging
resource "aws_dynamodb_table" "audit_log" {
  name           = "${var.project_name}-${var.environment}-audit-log"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "log_id"
  range_key      = "timestamp"

  attribute {
    name = "log_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "action"
    type = "S"
  }

  # Global Secondary Index for querying by user
  global_secondary_index {
    name            = "UserIdIndex"
    hash_key        = "user_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # Global Secondary Index for querying by action type
  global_secondary_index {
    name            = "ActionIndex"
    hash_key        = "action"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  # TTL for old logs (optional - keep logs for 2 years)
  ttl {
    attribute_name = "expires_at"
    enabled        = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-audit-log"
    Environment = var.environment
    Purpose     = "User activity audit logging"
  }
}

# DynamoDB table for file approval workflow
resource "aws_dynamodb_table" "file_approvals" {
  name           = "${var.project_name}-${var.environment}-file-approvals"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "file_id"

  attribute {
    name = "file_id"
    type = "S"
  }

  attribute {
    name = "status"
    type = "S"
  }

  attribute {
    name = "uploaded_at"
    type = "S"
  }

  # GSI for querying by status
  global_secondary_index {
    name            = "StatusIndex"
    hash_key        = "status"
    range_key       = "uploaded_at"
    projection_type = "ALL"
  }

  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-file-approvals"
    Environment = var.environment
    Purpose     = "File approval workflow tracking"
  }
}

# Lambda function for audit logging
resource "aws_lambda_function" "audit_logger" {
  filename         = "${path.module}/audit_logger.zip"
  function_name    = "${var.project_name}-${var.environment}-audit-logger"
  role            = aws_iam_role.audit_logger.arn
  handler         = "audit_logger.lambda_handler"
  runtime         = "python3.9"
  timeout         = 30

  environment {
    variables = {
      AUDIT_TABLE_NAME = aws_dynamodb_table.audit_log.name
      APPROVAL_TABLE_NAME = aws_dynamodb_table.file_approvals.name
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.audit_logger_policy,
    data.archive_file.audit_logger_zip
  ]
}

# Create zip file for Lambda
data "archive_file" "audit_logger_zip" {
  type        = "zip"
  source_file = "${path.module}/audit_logger.py"
  output_path = "${path.module}/audit_logger.zip"
}

# IAM role for audit logger Lambda
resource "aws_iam_role" "audit_logger" {
  name = "${var.project_name}-${var.environment}-audit-logger-role"

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

# IAM policy for audit logger
resource "aws_iam_role_policy" "audit_logger" {
  name = "${var.project_name}-${var.environment}-audit-logger-policy"
  role = aws_iam_role.audit_logger.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.audit_log.arn,
          "${aws_dynamodb_table.audit_log.arn}/index/*",
          aws_dynamodb_table.file_approvals.arn,
          "${aws_dynamodb_table.file_approvals.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach basic Lambda execution policy
resource "aws_iam_role_policy_attachment" "audit_logger_policy" {
  role       = aws_iam_role.audit_logger.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}