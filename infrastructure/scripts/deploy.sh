#!/bin/bash

# Kompletný deployment script
echo "🚀 Starting deployment..."

# 1. Deploy infraštruktúry
echo "📦 Deploying infrastructure with Terraform..."
terraform apply -var-file=dev.tfvars -auto-approve

if [ $? -ne 0 ]; then
    echo "❌ Terraform deployment failed!"
    exit 1
fi

# 2. Vygeneruj .env súbor
echo "⚙️ Generating .env file..."
./scripts/generate-env.sh

# 3. Install dependencies (ak nie sú nainštalované)
echo "📦 Installing frontend dependencies..."
cd ai-chat-amplify/ai-chat-amplify
npm install

# 4. Build aplikácie
echo "🔨 Building Next.js application..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

# 5. Výpis informácií
echo ""
echo "✅ Deployment completed successfully!"
echo ""
echo "🔐 AWS Resources created:"
echo "   - Cognito User Pool: $(cd ../.. && terraform output -raw cognito_user_pool_id)"
echo "   - S3 Storage Bucket: $(cd ../.. && terraform output -raw cognito_storage_bucket)"
echo "   - Region: $(cd ../.. && terraform output -raw region)"
echo ""
echo "🌐 To run locally:"
echo "   cd ai-chat-amplify/ai-chat-amplify"
echo "   npm run dev"
echo "   Open: http://localhost:3000"
echo ""
echo "🚀 For GLOBAL deployment:"
echo "   1. Push code to GitHub: git push origin main"
echo "   2. Get Amplify URL: terraform output amplify_app_url"
echo "   3. Your app will be globally accessible!"
echo ""
echo "🌍 IMPORTANT: Update dev.tfvars with your GitHub repo URL before terraform apply"
echo "   repository_url = \"https://github.com/YOUR-USERNAME/ai-chat-amplify\""