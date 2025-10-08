output "audit_table_name" {
  value = aws_dynamodb_table.audit_log.name
}

output "audit_table_arn" {
  value = aws_dynamodb_table.audit_log.arn
}

output "approval_table_name" {
  value = aws_dynamodb_table.file_approvals.name
}

output "approval_table_arn" {
  value = aws_dynamodb_table.file_approvals.arn
}

output "audit_logger_function_name" {
  value = aws_lambda_function.audit_logger.function_name
}

output "audit_logger_function_arn" {
  value = aws_lambda_function.audit_logger.arn
}