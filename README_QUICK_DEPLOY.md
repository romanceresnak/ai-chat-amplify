# 🚀 Jednoduchý AI Chat Assistant - Automatický Deployment

## ⚡ Jedno-príkazový deployment

```bash
./deploy.sh
```

To je všetko! 🎉

## 📋 Čo sa stane

1. **Terraform** vytvorí AWS infraštruktúru:
   - Cognito User Pool (prihlásenia)
   - S3 bucket (súbory)
   - IAM role (Bedrock permissions)

2. **Script** vygeneruje `.env.local` súbor

3. **Next.js** sa buildne a je pripravený na spustenie

## 🌐 Po deployment

### Lokálne testovanie:
```bash
cd ai-chat-amplify/ai-chat-amplify
npm run dev
# Otvorte: http://localhost:3000
```

### Produkčný deployment:

**Option 1: Vercel (Odporúčané)**
```bash
cd ai-chat-amplify/ai-chat-amplify
npx vercel --prod
# Nastavte environment variables z .env.local
```

**Option 2: Netlify**
```bash
cd ai-chat-amplify/ai-chat-amplify
npx netlify deploy --prod --dir=.next
```

**Option 3: AWS Amplify Console**
1. Commitnite kód do GitHubu
2. AWS Console → Amplify → "Host web app"
3. Pripojte GitHub repo
4. Pridajte environment variables z `.env.local`

## 🔐 Prvé prihlásenie

1. Otvorte aplikáciu
2. "Create Account" 
3. Email + silné heslo
4. Overte email kódom
5. Prihláste sa

## 🗑️ Cleanup

```bash
terraform destroy -var-file=dev.tfvars
```

## 🛠️ Troubleshooting

**Build error**: 
```bash
cd ai-chat-amplify/ai-chat-amplify && npm install
```

**Terraform error**:
```bash
terraform init
terraform plan -var-file=dev.tfvars
```

**Environment variables chýbajú**:
```bash
./scripts/generate-env.sh
```