# Outputs
output "documents_bucket_arn" {
  value = aws_s3_bucket.documents.arn
}

output "bucket_names" {
  value = {
    documents     = aws_s3_bucket.documents.id
    templates     = aws_s3_bucket.templates.id
    financial     = aws_s3_bucket.financial_data.id
    output        = aws_s3_bucket.output.id
    prompts       = aws_s3_bucket.prompts.id
  }
}

output "bucket_arns" {
  value = [
    aws_s3_bucket.documents.arn,
    aws_s3_bucket.templates.arn,
    aws_s3_bucket.financial_data.arn,
    aws_s3_bucket.output.arn,
    aws_s3_bucket.prompts.arn
  ]
}