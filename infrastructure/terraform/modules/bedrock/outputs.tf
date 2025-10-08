# Outputs
output "knowledge_base_id" {
  value = aws_bedrockagent_knowledge_base.main.id
}

output "agent_id" {
  value = aws_bedrockagent_agent.presentation_agent.id
}

output "agent_alias_id" {
  value = aws_bedrockagent_agent_alias.presentation_agent_alias.agent_alias_id
}

output "kb_sync_lambda_arn" {
  value = aws_lambda_function.kb_sync.arn
}

output "kb_sync_lambda_permission" {
  value = aws_lambda_permission.s3_invoke
}