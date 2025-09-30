# 🚀 AI Chat Assistant

AI-powered chat aplikácia postavená na AWS Amplify, Next.js a AWS Bedrock.

## 📋 Predpoklady

- Node.js 18+ a npm
- AWS účet
- AWS CLI nakonfigurované (voliteľné, ale odporúčané)

## 🔧 Inštalácia

1. **Nainštalujte dev závislosti pre Amplify** (ak ste to ešte neurobili):
```bash
npm install -D @aws-amplify/backend @aws-amplify/backend-cli
```

2. **Spustite Amplify sandbox**:
```bash
npm run sandbox
```
Počkajte, kým sa zobrazí "Successfully generated outputs" a vytvorí sa súbor `amplify_outputs.json`.

3. **V novom termináli spustite Next.js**:
```bash
npm run dev
```

Aplikácia bude dostupná na http://localhost:3000

## 🔐 Prvé prihlásenie

1. Otvorte aplikáciu
2. Kliknite na "Create Account"
3. Zadajte email a heslo (min. 8 znakov, veľké/malé písmená, čísla, symboly)
4. Dostanete overovací kód na email
5. Po overení sa môžete prihlásiť

## ⚙️ Konfigurácia

### Zmena AWS regiónu pre Bedrock

V súbore `components/ChatInterface.tsx` upravte región:
```typescript
const client = new BedrockRuntimeClient({
  region: 'us-east-1', // Zmeňte na váš preferovaný región
  credentials: session.credentials,
});
```

### Zmena Bedrock modelu

V súbore `components/ChatInterface.tsx` upravte model ID:
```typescript
const command = new InvokeModelCommand({
  modelId: 'anthropic.claude-3-5-sonnet-20241022-v2:0', // Môžete zmeniť na iný model
  // ...
});
```

## 📦 Štruktúra projektu

```
ai-chat-amplify/
├── amplify/
│   ├── auth/         # Cognito konfigurácia
│   ├── data/         # GraphQL schéma
│   ├── storage/      # S3 konfigurácia
│   └── backend.ts    # Backend konfigurácia
├── app/
│   ├── layout.tsx    # Root layout
│   └── page.tsx      # Hlavná stránka
├── components/
│   ├── AuthProvider.tsx      # Autentifikácia wrapper
│   ├── ChatInterface.tsx     # Chat UI s Bedrock
│   ├── ConfigureAmplify.tsx  # Amplify konfigurácia
│   └── UserMenu.tsx          # Užívateľské menu
└── package.json
```

## 🚀 Deployment

### Amplify Hosting (Odporúčané)

1. Commitnite kód do Git:
```bash
git init
git add .
git commit -m "Initial commit"
git push -u origin main
```

2. V AWS Console → Amplify:
   - Kliknite "New app" → "Host web app"
   - Pripojte váš Git repozitár
   - Amplify automaticky deteguje Next.js
   - Kliknite "Save and deploy"

### Manuálny deployment

```bash
# Deploy backend
npx ampx pipeline deploy --branch main --app-id <your-app-id>

# Build frontend
npm run build
```

## 🛠️ Užitočné príkazy

```bash
# Spustiť sandbox
npm run sandbox

# Zastaviť sandbox
npm run sandbox:delete

# Development server
npm run dev

# Build pre produkciu
npm run build
```

## 🔒 Security

- Heslo policy: Min. 8 znakov, veľké/malé písmená, čísla, symboly
- Email verifikácia: Povinná
- Session timeout: 1 hodina
- MFA: Voliteľná (TOTP)

## 📝 Poznámky

- Pre sandbox sa používa Amazon SES sandbox mode (max 200 emailov/deň)
- Pre produkciu požiadajte o vyňatie z SES sandbox
- Všetky súbory sa ukladajú do S3 s prefix `chat-files/`
- Chat história sa ukladá do DynamoDB cez GraphQL

## 🐛 Troubleshooting

**Problém**: "User pool client does not exist"
- **Riešenie**: `npm run sandbox:delete && npm run sandbox`

**Problém**: Email sa nedoručí
- **Riešenie**: Skontrolujte spam/junk folder alebo AWS SES limity

**Problém**: Network error pri prihlásení
- **Riešenie**: Uistite sa, že máte `amplify_outputs.json` a sandbox beží