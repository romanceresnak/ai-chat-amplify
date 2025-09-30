# REST API
resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.project_name}-${var.environment}-api"
  description = "ScribbeAI Presentation Generation API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }
}

# Resources and Methods
resource "aws_api_gateway_resource" "presentations" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "presentations"
}

resource "aws_api_gateway_method" "create_presentation" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.presentations.id
  http_method   = "POST"
  authorization = "AWS_IAM"
}

resource "aws_api_gateway_integration" "orchestrator" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presentations.id
  http_method = aws_api_gateway_method.create_presentation.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = var.lambda_invoke_arns.orchestrator
}

# Lambda permissions for API Gateway
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = var.lambda_function_arns.orchestrator
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# Deployment
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.presentations,
      aws_api_gateway_method.create_presentation,
      aws_api_gateway_integration.orchestrator,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment

  xray_tracing_enabled = true
}

# CloudWatch Logs
resource "aws_cloudwatch_log_group" "api_gateway" {
  name              = "/aws/apigateway/${var.project_name}-${var.environment}"
  retention_in_days = 30
}