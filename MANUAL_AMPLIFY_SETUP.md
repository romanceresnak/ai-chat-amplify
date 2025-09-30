# 🚀 Manuálne nastavenie AWS Amplify Hosting

## ✅ Stav infraštruktúry:
- **Cognito**: ✅ Vytvorené (`eu-west-1_j1F2pMlCe`)
- **S3 Storage**: ✅ Vytvorené (`scribbe-ai-dev-storage`)
- **Environment Variables**: ✅ Vygenerované v `.env.local`

## 🎯 Krok 1: Vytvorte Amplify App v AWS Console

1. **Otvorte AWS Console**: https://console.aws.amazon.com/amplify/
2. **Kliknite "New app" → "Host web app"**
3. **Vyberte "GitHub"** ako source
4. **Autorizujte GitHub** (ak prvýkrát)
5. **Vyberte repository**: `romanceresnak/ai-chat-amplify`
6. **Vyberte branch**: `main`

## 🔧 Krok 2: Nastavte Build settings

Amplify automaticky deteguje Next.js, ale overte build settings:

```yaml
version: 1
applications:
  - appRoot: ai-chat-amplify/ai-chat-amplify
    frontend:
      phases:
        preBuild:
          commands:
            - npm ci
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: .next
        files:
          - '**/*'
      cache:
        paths:
          - node_modules/**/*
```

## ⚙️ Krok 3: Pridajte Environment Variables

V Amplify Console → App settings → Environment variables:

```
NEXT_PUBLIC_USER_POOL_ID = eu-west-1_j1F2pMlCe
NEXT_PUBLIC_USER_POOL_CLIENT_ID = 45u01gjbok5m7mo3nr0hdqq70f
NEXT_PUBLIC_IDENTITY_POOL_ID = eu-west-1:41b0342c-0aea-4b4b-835e-83c4d38c48eb
NEXT_PUBLIC_AWS_REGION = eu-west-1
NEXT_PUBLIC_STORAGE_BUCKET = scribbe-ai-dev-storage
NEXT_PUBLIC_BEDROCK_REGION = us-east-1
```

## 🚀 Krok 4: Deploy

1. **Kliknite "Save and deploy"**
2. **Počkajte 3-5 minút** na build a deployment
3. **Získajte URL**: `https://main.d1234567890.amplifyapp.com`

## ✅ Po úspešnom deployment:

### 🌍 Vaša aplikácia bude dostupná globálne:
- **URL**: `https://main.d1234567890.amplifyapp.com`
- **SSL**: Automaticky
- **CDN**: Worldwww
- **Auto-scaling**: Ano

### 🔄 CI/CD je aktívne:
- Každý `git push origin main` = automatický redeploy
- Build logy v Amplify Console
- Rollback možný kedykoľvek

## 🧪 Testovanie aplikácie:

1. **Otvorte URL v prehliadači**
2. **Kliknite "Create Account"**
3. **Registrujte sa s emailom**
4. **Overte email kódom**
5. **Prihláste sa a testujte chat**

## 📊 Monitoring:

- **Amplify Console**: Build logs, traffic stats
- **CloudWatch**: Performance metrics  
- **Cognito Console**: User management

## 🎉 Hotovo!

Vaša AI Chat aplikácia je teraz:
- 🌍 **Globálne dostupná**
- 🔒 **Zabezpečená** s Cognito
- ⚡ **Rýchla** s CDN
- 🔄 **Automaticky aktualizovaná**

**Zdieľajte URL s kýmkoľvek!** 🚀