# OpenSearch Serverless Security Policy - must be created before collection
resource "aws_opensearchserverless_security_policy" "encryption" {
  name = "${var.project_name}-${var.environment}-enc"
  type = "encryption"
  
  policy = jsonencode({
    Rules = [
      {
        Resource = ["collection/${var.project_name}-${var.environment}-kb"]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = true
  })
}

# Network security policy - required for OpenSearch Serverless
resource "aws_opensearchserverless_security_policy" "network" {
  name = "${var.project_name}-${var.environment}-net"
  type = "network"
  
  policy = jsonencode([{
    Rules = [{
      Resource = ["collection/${var.project_name}-${var.environment}-kb"]
      ResourceType = "collection"
    }]
    AllowFromPublic = true
  }])
}

# OpenSearch Serverless Collection for Knowledge Base
resource "aws_opensearchserverless_collection" "knowledge_base" {
  name = "${var.project_name}-${var.environment}-kb"
  type = "VECTORSEARCH"
  
  depends_on = [
    aws_opensearchserverless_security_policy.encryption,
    aws_opensearchserverless_security_policy.network
  ]
}

# Wait for collection to be active
resource "time_sleep" "wait_for_collection" {
  depends_on = [aws_opensearchserverless_collection.knowledge_base]
  create_duration = "30s"
}

# Access policy for OpenSearch Serverless - must be created before index creation
resource "aws_opensearchserverless_access_policy" "knowledge_base" {
  name = "${var.project_name}-${var.environment}-ap"
  type = "data"
  
  policy = jsonencode([{
    Rules = [
      {
        Resource = ["collection/${aws_opensearchserverless_collection.knowledge_base.name}"]
        Permission = [
          "aoss:CreateCollectionItems",
          "aoss:UpdateCollectionItems",
          "aoss:DescribeCollectionItems"
        ]
        ResourceType = "collection"
      },
      {
        Resource = ["index/${aws_opensearchserverless_collection.knowledge_base.name}/*"]
        Permission = [
          "aoss:CreateIndex",
          "aoss:UpdateIndex",
          "aoss:DescribeIndex",
          "aoss:ReadDocument",
          "aoss:WriteDocument"
        ]
        ResourceType = "index"
      }
    ]
    Principal = [
      var.knowledge_base_role,
      var.agent_role,
      data.aws_caller_identity.current.arn
    ]
  }])
}

# Wait for access policy to propagate
resource "time_sleep" "wait_for_access_policy" {
  depends_on = [aws_opensearchserverless_access_policy.knowledge_base]
  create_duration = "60s"
}

# Use external Python script for index creation

# Create the OpenSearch index
resource "null_resource" "create_opensearch_index" {
  depends_on = [
    aws_opensearchserverless_collection.knowledge_base,
    aws_opensearchserverless_access_policy.knowledge_base,
    time_sleep.wait_for_collection,
    time_sleep.wait_for_access_policy
  ]

  provisioner "local-exec" {
    command = "python3 -m venv /tmp/terraform_venv && source /tmp/terraform_venv/bin/activate && python3 -m pip install requests requests-aws4auth boto3 && REGION_NAME='${data.aws_region.current.name}' COLLECTION_NAME='${aws_opensearchserverless_collection.knowledge_base.name}' python3 ${path.module}/create_opensearch_index.py"
  }
  
  triggers = {
    collection_id = aws_opensearchserverless_collection.knowledge_base.id
    timestamp = timestamp()
  }
}

# Wait for index creation to complete
resource "time_sleep" "wait_for_index" {
  depends_on = [null_resource.create_opensearch_index]
  create_duration = "30s"
}

# Bedrock Knowledge Base
resource "aws_bedrockagent_knowledge_base" "main" {
  name        = "${var.project_name}-${var.environment}-kb-fixed"
  description = "Knowledge base for ScribbeAI presentations"
  role_arn    = var.knowledge_base_role

  knowledge_base_configuration {
    type = "VECTOR"
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${data.aws_region.current.name}::foundation-model/cohere.embed-english-v3"
    }
  }

  storage_configuration {
    type = "OPENSEARCH_SERVERLESS"
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.knowledge_base.arn
      vector_index_name = "scribbe-vectors-v2"
      
      field_mapping {
        vector_field   = "embedding"
        text_field     = "content"
        metadata_field = "metadata"
      }
    }
  }
  
  depends_on = [
    aws_opensearchserverless_access_policy.knowledge_base,
    null_resource.create_opensearch_index,
    time_sleep.wait_for_index
  ]
}

# Data Source for Knowledge Base
resource "aws_bedrockagent_data_source" "s3_documents" {
  name              = "${var.project_name}-documents-v2"
  knowledge_base_id = aws_bedrockagent_knowledge_base.main.id
  
  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = var.s3_data_source_bucket
    }
  }
  
  lifecycle {
    create_before_destroy = true
  }
}

# Bedrock Agent
resource "aws_bedrockagent_agent" "presentation_agent" {
  agent_name              = "${var.project_name}-${var.environment}-agent-standalone"
  agent_resource_role_arn = var.agent_role
  foundation_model        = "eu.anthropic.claude-3-5-sonnet-20240620-v1:0"
  idle_session_ttl_in_seconds = 600
  
  instruction = <<-EOT
    You are an expert financial presentation creator for ScribbeAI.
    Your role is to:
    1. Analyze uploaded documents from investment banks and asset management firms
    2. Extract key financial data and insights  
    3. Generate detailed specifications for professional PowerPoint slides and charts
    4. Create comprehensive slide content including charts, data visualizations, and formatting instructions
    5. Ensure accuracy and compliance with financial reporting standards
    
    When creating slides, provide detailed specifications including:
    - Chart types and data series
    - Color schemes and styling
    - Layout and positioning
    - Text content and formatting
    
    Always maintain professional tone and accuracy in financial data representation.
  EOT
  
  prepare_agent = true
}

# Agent Knowledge Base Association - DISABLED to use custom prompt
# resource "aws_bedrockagent_agent_knowledge_base_association" "kb_association" {
#   agent_id              = aws_bedrockagent_agent.presentation_agent.id
#   description          = "Knowledge base for financial documents"
#   knowledge_base_id    = aws_bedrockagent_knowledge_base.main.id
#   knowledge_base_state = "ENABLED"
# }

# Lambda function for automatic knowledge base sync
resource "aws_lambda_function" "kb_sync" {
  filename         = "${path.module}/sync_lambda.zip"
  function_name    = "${var.project_name}-${var.environment}-kb-sync"
  role            = aws_iam_role.lambda_kb_sync.arn
  handler         = "sync_lambda.lambda_handler"
  runtime         = "python3.9"
  timeout         = 60

  environment {
    variables = {
      KNOWLEDGE_BASE_ID = aws_bedrockagent_knowledge_base.main.id
      DATA_SOURCE_ID    = aws_bedrockagent_data_source.s3_documents.data_source_id
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_kb_sync_policy,
    data.archive_file.lambda_kb_sync_zip
  ]
}

# Create zip file for Lambda
data "archive_file" "lambda_kb_sync_zip" {
  type        = "zip"
  source_file = "${path.module}/sync_lambda.py"
  output_path = "${path.module}/sync_lambda.zip"
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_kb_sync" {
  name = "${var.project_name}-${var.environment}-lambda-kb-sync"

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

# IAM policy for Lambda to access Bedrock and CloudWatch
resource "aws_iam_role_policy" "lambda_kb_sync" {
  name = "${var.project_name}-${var.environment}-lambda-kb-sync-policy"
  role = aws_iam_role.lambda_kb_sync.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:*",
          "bedrock-agent:*",
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
resource "aws_iam_role_policy_attachment" "lambda_kb_sync_policy" {
  role       = aws_iam_role.lambda_kb_sync.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Lambda permission for S3 to invoke
resource "aws_lambda_permission" "s3_invoke" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.kb_sync.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = var.s3_data_source_bucket
}

# Agent Alias
resource "aws_bedrockagent_agent_alias" "presentation_agent_alias" {
  agent_alias_name = "${var.environment}-alias"
  agent_id         = aws_bedrockagent_agent.presentation_agent.id
  description      = "Alias for ${var.environment} environment - custom prompt"
  
  depends_on = [
    aws_bedrockagent_agent.presentation_agent
  ]
}

data "aws_region" "current" {}

data "aws_caller_identity" "current" {}