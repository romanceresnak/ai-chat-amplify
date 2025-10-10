# S3 bucket for Lambda deployment packages
resource "aws_s3_bucket" "lambda_deployment" {
  bucket = "${var.project_name}-${var.environment}-lambda-deployment"
}

# Ensure the layer ZIP file exists (create if needed)
resource "null_resource" "ensure_layer_exists" {
  triggers = {
    layer_check = fileexists("${path.module}/python-deps-layer.zip") ? "exists" : "missing"
  }
  
  provisioner "local-exec" {
    command = <<-EOT
      if [ ! -f "${path.module}/python-deps-layer.zip" ]; then
        echo "Lambda layer not found, creating..."
        cd ${path.module}
        if command -v python3 &> /dev/null; then
          python3 create_simple_layer.py
        elif command -v python &> /dev/null; then
          python create_simple_layer.py
        else
          echo "Error: Python not found. Please install Python 3."
          exit 1
        fi
      else
        echo "Lambda layer already exists"
      fi
    EOT
    interpreter = ["bash", "-c"]
  }
}

# Upload Lambda layer to S3
resource "aws_s3_object" "python_deps_layer" {
  bucket = aws_s3_bucket.lambda_deployment.id
  key    = "layers/python-deps-layer.zip"
  source = "${path.module}/python-deps-layer.zip"
  
  depends_on = [null_resource.ensure_layer_exists]
}

# Lambda Layer with all Python dependencies
resource "aws_lambda_layer_version" "python_deps" {
  layer_name          = "${var.project_name}-${var.environment}-python-deps"
  description         = "Python dependencies including python-pptx, langchain, boto3"
  
  s3_bucket           = aws_s3_bucket.lambda_deployment.id
  s3_key              = aws_s3_object.python_deps_layer.key
  
  compatible_runtimes = ["python3.11"]
  
  depends_on = [aws_s3_object.python_deps_layer]
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
      USE_LANGCHAIN        = "true"
      TAVILY_API_KEY       = "tvly-xxxxx"    # Nahraď svojím API kľúčom
      SERPAPI_API_KEY      = "xxxxx"         # Nahraď svojím API kľúčom
    }
  }

  layers = [aws_lambda_layer_version.python_deps.arn]

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

  layers = [aws_lambda_layer_version.python_deps.arn]
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

  layers = [aws_lambda_layer_version.python_deps.arn]
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