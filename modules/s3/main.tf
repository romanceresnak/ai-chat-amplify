# Documents bucket
resource "aws_s3_bucket" "documents" {
  bucket = "${var.project_name}-${var.environment}-documents"
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "AES256"
    }
  }
}

# Templates bucket
resource "aws_s3_bucket" "templates" {
  bucket = "${var.project_name}-${var.environment}-templates"
}

resource "aws_s3_bucket_versioning" "templates" {
  bucket = aws_s3_bucket.templates.id
  
  versioning_configuration {
    status = "Enabled"
  }
}

# Financial data bucket
resource "aws_s3_bucket" "financial_data" {
  bucket = "${var.project_name}-${var.environment}-financial-data"
}

# Output bucket
resource "aws_s3_bucket" "output" {
  bucket = "${var.project_name}-${var.environment}-output"
}

resource "aws_s3_bucket_lifecycle_configuration" "output" {
  bucket = aws_s3_bucket.output.id

  rule {
    id     = "delete-old-outputs"
    status = "Enabled"

    filter {}

    expiration {
      days = var.retention_days
    }
  }
}

# Prompts bucket
resource "aws_s3_bucket" "prompts" {
  bucket = "${var.project_name}-${var.environment}-prompts"
}

# Bucket policies
resource "aws_s3_bucket_policy" "documents" {
  bucket = aws_s3_bucket.documents.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowBedrockAccess"
        Effect    = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
      }
    ]
  })
}

