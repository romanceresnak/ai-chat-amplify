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
  authorization = "NONE"
}

resource "aws_api_gateway_method" "list_presentations" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.presentations.id
  http_method   = "GET"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "orchestrator" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presentations.id
  http_method = aws_api_gateway_method.create_presentation.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = var.lambda_invoke_arns.orchestrator
}

resource "aws_api_gateway_integration" "list_orchestrator" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presentations.id
  http_method = aws_api_gateway_method.list_presentations.http_method

  integration_http_method = "POST"
  type                   = "AWS_PROXY"
  uri                    = var.lambda_invoke_arns.orchestrator
}

# CORS Configuration
resource "aws_api_gateway_method" "presentations_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.presentations.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "presentations_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presentations.id
  http_method = aws_api_gateway_method.presentations_options.http_method

  type = "MOCK"

  request_templates = {
    "application/json" = jsonencode({
      statusCode = 200
    })
  }
}

resource "aws_api_gateway_method_response" "presentations_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presentations.id
  http_method = aws_api_gateway_method.presentations_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }

  response_models = {
    "application/json" = "Empty"
  }
}

resource "aws_api_gateway_integration_response" "presentations_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.presentations.id
  http_method = aws_api_gateway_method.presentations_options.http_method
  status_code = aws_api_gateway_method_response.presentations_options.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"
    "method.response.header.Access-Control-Allow-Methods" = "'OPTIONS,POST,GET'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
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
      aws_api_gateway_method.list_presentations,
      aws_api_gateway_integration.orchestrator,
      aws_api_gateway_integration.list_orchestrator,
      aws_api_gateway_method.presentations_options,
      aws_api_gateway_integration.presentations_options,
      aws_api_gateway_method_response.presentations_options,
      aws_api_gateway_integration_response.presentations_options,
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