output "patterns_table_name" {
  value = aws_dynamodb_table.patterns.name
}

output "patterns_table_arn" {
  value = aws_dynamodb_table.patterns.arn
}

output "findings_table_name" {
  value = aws_dynamodb_table.client_findings.name
}

output "findings_table_arn" {
  value = aws_dynamodb_table.client_findings.arn
}

output "pattern_analyzer_function_name" {
  value = aws_lambda_function.pattern_analyzer.function_name
}

output "pattern_analyzer_function_arn" {
  value = aws_lambda_function.pattern_analyzer.arn
}