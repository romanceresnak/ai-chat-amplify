# S3 bucket for Lambda deployment packages
resource "aws_s3_bucket" "lambda_deployment" {
  bucket = "${var.project_name}-${var.environment}-lambda-deployment"
}

# Upload Lambda layer to S3
resource "aws_s3_object" "python_libs_layer" {
  bucket = aws_s3_bucket.lambda_deployment.id
  key    = "layers/python-libs.zip"
  source = "${path.module}/layers/python-libs.zip"
  etag   = filemd5("${path.module}/layers/python-libs.zip")
}

# Lambda Layers
resource "aws_lambda_layer_version" "python_libs" {
  layer_name = "${var.project_name}-python-libs"
  
  s3_bucket = aws_s3_bucket.lambda_deployment.id
  s3_key    = aws_s3_object.python_libs_layer.key
  
  compatible_runtimes = ["python3.11"]
  
  depends_on = [aws_s3_object.python_libs_layer]
}

# Orchestrator Lambda
resource "aws_lambda_function" "orchestrator" {
  filename         = data.archive_file.orchestrator.output_path
  function_name    = "${var.project_name}-${var.environment}-orchestrator"
  role            = var.lambda_role_arn
  handler         = "index.lambda_handler"
  runtime         = "python3.11"
  timeout         = 300
  memory_size     = 1024

  environment {
    variables = {
      ENVIRONMENT           = var.environment
      BEDROCK_KB_ID        = var.bedrock_kb_id
      DOCUMENTS_BUCKET     = var.s3_buckets.documents
      TEMPLATES_BUCKET     = var.s3_buckets.templates
      OUTPUT_BUCKET        = var.s3_buckets.output
      PROMPTS_BUCKET       = var.s3_buckets.prompts
      USE_LANGCHAIN        = "false"  # Can be toggled to "true" to use LangChain orchestrator
      TAVILY_API_KEY       = ""       # Add your Tavily API key here or use AWS Secrets Manager
      SERPAPI_API_KEY      = ""       # Add your SerpAPI key here or use AWS Secrets Manager
    }
  }

  layers = [aws_lambda_layer_version.python_libs.arn]

  dynamic "vpc_config" {
    for_each = var.vpc_config != null ? [1] : []
    content {
      subnet_ids         = var.vpc_config.subnet_ids
      security_group_ids = var.vpc_config.security_group_ids
    }
  }
}

# Content Generator Lambda
resource "aws_lambda_function" "content_generator" {
  filename         = data.archive_file.content_generator.output_path
  function_name    = "${var.project_name}-${var.environment}-content-generator"
  role            = var.lambda_role_arn
  handler         = "index.lambda_handler"
  runtime         = "python3.11"
  timeout         = 120
  memory_size     = 512

  environment {
    variables = {
      ENVIRONMENT      = var.environment
      BEDROCK_KB_ID   = var.bedrock_kb_id
    }
  }

  layers = [aws_lambda_layer_version.python_libs.arn]
}

# Template Processor Lambda
resource "aws_lambda_function" "template_processor" {
  filename         = data.archive_file.template_processor.output_path
  function_name    = "${var.project_name}-${var.environment}-template-processor"
  role            = var.lambda_role_arn
  handler         = "index.lambda_handler"
  runtime         = "python3.11"
  timeout         = 120
  memory_size     = 512

  environment {
    variables = {
      ENVIRONMENT       = var.environment
      TEMPLATES_BUCKET = var.s3_buckets.templates
      OUTPUT_BUCKET    = var.s3_buckets.output
    }
  }

  layers = [aws_lambda_layer_version.python_libs.arn]
}

# Archive files for Lambda deployment
data "archive_file" "orchestrator" {
  type        = "zip"
  source_dir  = "${path.root}/../../application/backend/orchestrator"
  output_path = "${path.module}/orchestrator.zip"
}

data "archive_file" "content_generator" {
  type        = "zip"
  source_dir  = "${path.root}/../../application/backend/content-generator"
  output_path = "${path.module}/content-generator.zip"
}

data "archive_file" "template_processor" {
  type        = "zip"
  source_dir  = "${path.root}/../../application/backend/template-processor"
  output_path = "${path.module}/template-processor.zip"
}

# EventBridge Rule for scheduled processing
resource "aws_cloudwatch_event_rule" "scheduled_processing" {
  name                = "${var.project_name}-scheduled-processing"
  description         = "Trigger scheduled presentation processing"
  schedule_expression = "rate(1 hour)"
  state              = "DISABLED"
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.scheduled_processing.name
  target_id = "OrchestratorLambdaTarget"
  arn       = aws_lambda_function.orchestrator.arn
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.orchestrator.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.scheduled_processing.arn
}