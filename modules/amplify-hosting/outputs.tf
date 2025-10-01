output "app_id" {
  description = "Amplify App ID"
  value       = var.repository_url != "" ? aws_amplify_app.main[0].id : "Not created - no repository URL"
}

output "app_url" {
  description = "Default Amplify app URL"
  value       = var.repository_url != "" ? "https://${aws_amplify_branch.main[0].branch_name}.${aws_amplify_app.main[0].id}.amplifyapp.com" : "Not created - no repository URL"
}

output "custom_domain_url" {
  description = "Custom domain URL if configured"
  value       = var.custom_domain != "" && var.repository_url != "" ? "https://${var.custom_domain}" : null
}