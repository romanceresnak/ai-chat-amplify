# Outputs
output "lambda_role_arn" {
  value = aws_iam_role.lambda_role.arn
}

output "bedrock_kb_role_arn" {
  value = aws_iam_role.bedrock_kb_role.arn
}

output "bedrock_agent_role_arn" {
  value = aws_iam_role.bedrock_agent_role.arn
}