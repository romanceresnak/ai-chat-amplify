# Outputs
output "function_arns" {
  value = {
    orchestrator       = aws_lambda_function.orchestrator.arn
    content_generator  = aws_lambda_function.content_generator.arn
    template_processor = aws_lambda_function.template_processor.arn
  }
}

output "invoke_arns" {
  value = {
    orchestrator       = aws_lambda_function.orchestrator.invoke_arn
    content_generator  = aws_lambda_function.content_generator.invoke_arn
    template_processor = aws_lambda_function.template_processor.invoke_arn
  }
}