# 🚀 AI Chat Assistant s Terraform a AWS Cognito

Kompletný návod na nasadenie AI Chat aplikácie pomocou Terraform pre infraštruktúru a Next.js pre frontend.

## 📋 Architektúra

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────────┐
│   Next.js App   │────▶│   Cognito    │────▶│  Bedrock API    │
└─────────────────┘     └──────────────┘     └─────────────────┘
         │                      │
         ▼                      ▼
┌─────────────────┐     ┌──────────────┐
│   S3 Storage    │     │ Identity Pool │
└─────────────────┘     └──────────────┘
```

## 🔧 Krok 1: Deploy infraštruktúry pomocou Terraform

### 1.1 Inicializácia Terraform
```bash
terraform init
```

### 1.2 Vytvorenie workspace (ak používate)
```bash
terraform workspace new dev  # alebo prod
```

### 1.3 Deploy infraštruktúry
```bash
# Skontrolujte, čo sa vytvorí
terraform plan -var-file=dev.tfvars

# Aplikujte zmeny
terraform apply -var-file=dev.tfvars
```

### 1.4 Vygenerujte .env súbor pre frontend
```bash
# Spustite script na automatické vytvorenie .env.local
./scripts/generate-env.sh
```

## 🎯 Krok 2: Setup frontend aplikácie

### 2.1 Prejdite do frontend priečinka
```bash
cd ai-chat-amplify/ai-chat-amplify
```

### 2.2 Nainštalujte závislosti
```bash
npm install

# Ak máte problémy s npm cache:
npm cache clean --force
```

### 2.3 Overte .env.local súbor
Skontrolujte, že súbor `.env.local` obsahuje správne hodnoty z Terraform:
```env
NEXT_PUBLIC_USER_POOL_ID=eu-west-1_xxxxx
NEXT_PUBLIC_USER_POOL_CLIENT_ID=xxxxxxxxxxxxx
NEXT_PUBLIC_IDENTITY_POOL_ID=eu-west-1:xxxxx-xxxx-xxxx
NEXT_PUBLIC_AWS_REGION=eu-west-1
NEXT_PUBLIC_STORAGE_BUCKET=project-dev-storage
```

### 2.4 Spustite aplikáciu lokálne
```bash
npm run dev
```

Aplikácia bude dostupná na http://localhost:3000

## 🔐 Krok 3: Prvý používateľ a testovanie

### 3.1 Registrácia
1. Otvorte aplikáciu v prehliadači
2. Kliknite na "Create Account"
3. Zadajte:
   - Email: váš email
   - Heslo: min. 8 znakov, veľké/malé písmená, čísla, symboly

### 3.2 Verifikácia emailu
1. Skontrolujte email pre verifikačný kód
2. Zadajte 6-ciferný kód v aplikácii

### 3.3 Prihlásenie
Po verifikácii sa môžete prihlásiť s emailom a heslom

## 🛠️ Správa používateľov cez AWS CLI

### Vytvorenie admin používateľa
```bash
# Získajte User Pool ID z Terraform outputs
USER_POOL_ID=$(terraform output -raw cognito_user_pool_id)

# Vytvorte admin používateľa
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username admin@example.com \
  --user-attributes Name=email,Value=admin@example.com Name=email_verified,Value=true \
  --temporary-password "TempPass123!" \
  --message-action SUPPRESS
```

### Zoznam používateľov
```bash
aws cognito-idp list-users --user-pool-id $USER_POOL_ID
```

### Reset hesla
```bash
aws cognito-idp admin-reset-user-password \
  --user-pool-id $USER_POOL_ID \
  --username user@example.com
```

## 📊 Monitoring v AWS Console

### Cognito Dashboard
1. AWS Console → Cognito → User Pools
2. Vyberte váš pool (názov: `project-dev-user-pool`)
3. Tu môžete:
   - Vidieť používateľov
   - Spravovať MFA nastavenia
   - Konfigurovať email templates
   - Monitorovať prihlásenia

### CloudWatch Logs
- User pool logs: `/aws/cognito/userpools/{region}_{pool-id}`
- Obsahuje: prihlásenia, registrácie, chyby

## 🚀 Deployment do produkcie

### Option 1: Amplify Hosting
```bash
# V ai-chat-amplify/ai-chat-amplify priečinku
git init
git add .
git commit -m "Initial commit"
git push origin main

# Potom v AWS Console nastavte Amplify Hosting
# a pridajte environment variables z .env.local
```

### Option 2: Vercel
```bash
vercel --prod
# Pridajte všetky NEXT_PUBLIC_* premenné v Vercel dashboard
```

### Option 3: Custom deployment
```bash
npm run build
# Deploy 'out' priečinok na váš hosting
```

## 🔄 Aktualizácia infraštruktúry

Pri zmene Terraform kódu:
```bash
# 1. Aplikujte zmeny
terraform apply -var-file=dev.tfvars

# 2. Vygenerujte nový .env súbor
./scripts/generate-env.sh

# 3. Reštartujte Next.js app
```

## ⚠️ Dôležité bezpečnostné poznámky

1. **Nikdy necommitujte .env.local súbor** - pridajte ho do .gitignore
2. **Používajte silné heslá** - Cognito vynucuje policy automaticky
3. **Povoľte MFA pre produkciu** - zmeňte `mfa_configuration = "ON"` v Terraform
4. **Monitorujte CloudWatch** - nastavte alarmy pre neúspešné prihlásenia
5. **Pravidelne rotujte credentials** - najmä pre admin účty

## 🐛 Troubleshooting

### "Network error" pri prihlásení
- Overte, že máte správne hodnoty v .env.local
- Skontrolujte, či Cognito resources existujú: `terraform show`

### Email sa nedoručí
- Cognito používa AWS SES v sandbox mode (limit 200/deň)
- Pre produkciu požiadajte o SES production access

### "Invalid UserPoolId"
- Znovu vygenerujte .env: `./scripts/generate-env.sh`
- Reštartujte Next.js server

### Terraform apply zlyhá
```bash
# Skontrolujte state
terraform state list

# Ak potrebné, importujte existujúce resources
terraform import module.cognito.aws_cognito_user_pool.main eu-west-1_xxxxx
```

## 📝 Štruktúra Terraform modulov

```
project/
├── modules/
│   ├── cognito/
│   │   ├── main.tf       # User Pool, Identity Pool, IAM
│   │   ├── variables.tf  # Konfiguračné premenné
│   │   └── outputs.tf    # Export IDs pre frontend
│   └── ...ostatné moduly
├── main.tf               # Hlavný Terraform súbor
├── dev.tfvars           # Development hodnoty
└── scripts/
    └── generate-env.sh  # Script na generovanie .env
```

## 🔗 Užitočné odkazy

- [AWS Cognito dokumentácia](https://docs.aws.amazon.com/cognito/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest)
- [Next.js deployment](https://nextjs.org/docs/deployment)