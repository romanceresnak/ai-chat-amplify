# Infrastructure

Terraform configuration for Scribbe AI application infrastructure.

## Structure

- `main.tf` - Main terraform configuration
- `variables.tf` - Input variables
- `outputs.tf` - Output values
- `modules/` - Reusable terraform modules
- `environments/` - Environment-specific configurations

## Deployment

```bash
terraform init
terraform plan -var-file="environments/dev.tfvars"
terraform apply -var-file="environments/dev.tfvars"
```

## Modules

- `amplify-hosting` - Amplify app and hosting
- `api-gateway` - REST API configuration
- `bedrock` - AI model access and configuration
- `cognito` - User authentication
- `iam` - IAM roles and policies
- `lambda` - Lambda functions
- `networking` - VPC and networking
- `s3` - Storage buckets