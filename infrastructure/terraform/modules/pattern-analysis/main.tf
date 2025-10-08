# DynamoDB table for storing discovered patterns
resource "aws_dynamodb_table" "patterns" {
  name           = "${var.project_name}-${var.environment}-patterns"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "pattern_id"
  range_key      = "discovered_at"

  attribute {
    name = "pattern_id"
    type = "S"
  }

  attribute {
    name = "discovered_at"
    type = "S"
  }

  attribute {
    name = "pattern_type"
    type = "S"
  }

  attribute {
    name = "confidence_score"
    type = "N"
  }

  # GSI for querying by pattern type
  global_secondary_index {
    name     = "PatternTypeIndex"
    hash_key = "pattern_type"
    range_key = "confidence_score"
  }

  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-patterns"
    Environment = var.environment
    Purpose     = "Pattern recognition and learning"
  }
}

# DynamoDB table for client findings and trends
resource "aws_dynamodb_table" "client_findings" {
  name           = "${var.project_name}-${var.environment}-client-findings"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "finding_id"
  range_key      = "created_at"

  attribute {
    name = "finding_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  attribute {
    name = "client_id"
    type = "S"
  }

  attribute {
    name = "category"
    type = "S"
  }

  # GSI for querying by client
  global_secondary_index {
    name     = "ClientIndex"
    hash_key = "client_id"
    range_key = "created_at"
  }

  # GSI for querying by category
  global_secondary_index {
    name     = "CategoryIndex"
    hash_key = "category"
    range_key = "created_at"
  }

  # Enable point-in-time recovery
  point_in_time_recovery {
    enabled = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-client-findings"
    Environment = var.environment
    Purpose     = "Client findings and trend analysis"
  }
}

# Lambda function for pattern analysis
resource "aws_lambda_function" "pattern_analyzer" {
  filename         = "${path.module}/pattern_analyzer.zip"
  function_name    = "${var.project_name}-${var.environment}-pattern-analyzer"
  role            = aws_iam_role.pattern_analyzer.arn
  handler         = "pattern_analyzer.lambda_handler"
  runtime         = "python3.9"
  timeout         = 300
  memory_size     = 1024

  environment {
    variables = {
      PATTERNS_TABLE_NAME = aws_dynamodb_table.patterns.name
      FINDINGS_TABLE_NAME = aws_dynamodb_table.client_findings.name
      KNOWLEDGE_BASE_ID   = var.knowledge_base_id
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.pattern_analyzer_policy,
    data.archive_file.pattern_analyzer_zip
  ]
}

# Create zip file for Lambda
data "archive_file" "pattern_analyzer_zip" {
  type        = "zip"
  source_file = "${path.module}/pattern_analyzer.py"
  output_path = "${path.module}/pattern_analyzer.zip"
}

# IAM role for pattern analyzer Lambda
resource "aws_iam_role" "pattern_analyzer" {
  name = "${var.project_name}-${var.environment}-pattern-analyzer-role"

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

# IAM policy for pattern analyzer
resource "aws_iam_role_policy" "pattern_analyzer" {
  name = "${var.project_name}-${var.environment}-pattern-analyzer-policy"
  role = aws_iam_role.pattern_analyzer.id

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
          aws_dynamodb_table.patterns.arn,
          "${aws_dynamodb_table.patterns.arn}/index/*",
          aws_dynamodb_table.client_findings.arn,
          "${aws_dynamodb_table.client_findings.arn}/index/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:*",
          "bedrock-agent:*"
        ]
        Resource = "*"
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
resource "aws_iam_role_policy_attachment" "pattern_analyzer_policy" {
  role       = aws_iam_role.pattern_analyzer.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# EventBridge rule to trigger pattern analysis daily
resource "aws_cloudwatch_event_rule" "daily_pattern_analysis" {
  name                = "${var.project_name}-${var.environment}-daily-pattern-analysis"
  description         = "Trigger pattern analysis daily"
  schedule_expression = "cron(0 2 * * ? *)"  # Run at 2 AM UTC daily
}

# EventBridge target
resource "aws_cloudwatch_event_target" "pattern_analyzer_target" {
  rule      = aws_cloudwatch_event_rule.daily_pattern_analysis.name
  target_id = "PatternAnalyzerTarget"
  arn       = aws_lambda_function.pattern_analyzer.arn
}

# Lambda permission for EventBridge to invoke
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.pattern_analyzer.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_pattern_analysis.arn
}