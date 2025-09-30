# 🌍 Globálny Deployment AI Chat Assistant

Kompletný návod na nasadenie aplikácie pre verejné použitie s automatickým CI/CD.

## 🚀 Krok 1: Vytvorte GitHub Repository

```bash
# V priečinku projektu
git init
git add .
git commit -m "Initial AI Chat Assistant"

# Vytvorte repository na GitHub.com a potom:
git remote add origin https://github.com/YOUR-USERNAME/ai-chat-amplify
git push -u origin main
```

## ⚙️ Krok 2: Aktualizujte Terraform konfiguráciu

Upravte `dev.tfvars`:
```hcl
# Zmeňte repository_url na váš GitHub repo
repository_url = "https://github.com/YOUR-USERNAME/ai-chat-amplify"
```

## 🏗️ Krok 3: Deploy infraštruktúry

```bash
# Spustite Terraform
terraform init
terraform apply -var-file=dev.tfvars

# Počkajte na dokončenie (3-5 minút)
```

## 🔗 Krok 4: Získajte URL aplikácie

```bash
# Získajte Amplify URL
terraform output amplify_app_url

# Výstup bude niečo ako:
# https://main.d1234567890.amplifyapp.com
```

## 🎯 Krok 5: Nastavte GitHub Secrets

V GitHub repository → Settings → Secrets and variables → Actions:

```bash
# Získajte hodnoty z Terraform:
terraform output cognito_user_pool_id
terraform output cognito_user_pool_client_id  
terraform output cognito_identity_pool_id
terraform output region
terraform output cognito_storage_bucket
```

Pridajte tieto GitHub Secrets:
- `NEXT_PUBLIC_USER_POOL_ID`
- `NEXT_PUBLIC_USER_POOL_CLIENT_ID`
- `NEXT_PUBLIC_IDENTITY_POOL_ID`
- `NEXT_PUBLIC_AWS_REGION`
- `NEXT_PUBLIC_STORAGE_BUCKET`

## 🔄 Krok 6: Automatický deployment

AWS Amplify automaticky:
1. **Deteguje push** do main branch
2. **Buildne** aplikáciu s environment variables
3. **Deployuje** na globálnu URL
4. **Poskytne SSL** certifikát zadarmo

## 🌐 Krok 7: Verejný prístup

**Vaša aplikácia je teraz verejne dostupná na:**
```
https://main.d1234567890.amplifyapp.com
```

### Funkcie:
✅ **Globálny prístup** - ktokoľvek na svete  
✅ **SSL/HTTPS** - bezpečné pripojenie  
✅ **CDN** - rýchle načítanie worldwide  
✅ **Auto-scaling** - zvládne tisíce používateľov  
✅ **CI/CD** - automatické aktualizácie z GitHub  

## 📊 Monitoring a správa

### AWS Console - Amplify
1. AWS Console → Amplify → Vaša app
2. Môžete vidieť:
   - Build históriu
   - Traffic štatistiky  
   - Performance metrics
   - Logs a errors

### AWS Console - Cognito
1. AWS Console → Cognito → User Pools
2. Správa používateľov:
   - Registrovaní používatelia
   - Prihlásenia/odhlásenia
   - Reset hesiel

## 🔒 Bezpečnosť pre produkciu

### 1. Povolte MFA (odporúčané)
V `modules/cognito/variables.tf`:
```hcl
variable "mfa_configuration" {
  default = "ON"  # Zmeniť z "OPTIONAL" na "ON"
}
```

### 2. Nastavte silnejšie heslo policy
```hcl
variable "password_policy" {
  default = {
    minimum_length = 12  # Zmeniť z 8 na 12
    # ... ostatné nastavenia
  }
}
```

### 3. Email limity
- Cognito má limit 200 emailov/deň v sandbox mode
- Pre produkciu: AWS Console → SES → Request production access

## 💰 Náklady (odhad)

Pre **1000 aktívnych používateľov/mesiac**:
- **Cognito**: $5-10/mesiac
- **Amplify Hosting**: $1-5/mesiac  
- **S3 Storage**: $1-3/mesiac
- **Bedrock API**: $10-50/mesiac (závisí od používania)

**Celkom: ~$20-70/mesiac**

## 🎚️ Škálovanie

### Pre viac používateľov:
1. **Bedrock**: Automaticky škáluje
2. **Cognito**: Do 10M používateľov
3. **Amplify**: Automatický CDN + scaling
4. **S3**: Neobmedzené úložisko

### Performance optimalizácia:
1. **CloudFront**: Už zahrnuté v Amplify
2. **Multi-region**: Deploy do viacerých regiónov
3. **Database**: Pridajte DynamoDB pre chat históriu

## 🔄 Aktualizácie

### Code zmeny:
```bash
git add .
git commit -m "Update features"
git push origin main
# Amplify automaticky rebuildne a deployuje
```

### Infrastructure zmeny:
```bash
terraform apply -var-file=dev.tfvars
# Aktualizuje AWS resources
```

## 🎨 Custom doména (voliteľné)

### 1. Kúpte doménu (napr. Route53)
### 2. Upravte dev.tfvars:
```hcl
custom_domain = "yourdomain.com"
```
### 3. Reapply Terraform:
```bash
terraform apply -var-file=dev.tfvars
```

## 🚨 Troubleshooting

### Build fails:
- Skontrolujte GitHub Secrets
- Pozrite Amplify Console → Build logs

### Users can't register:
- Skontrolujte email delivery v Cognito
- Možný SES sandbox limit

### App slow:
- Skontrolujte Bedrock region proximity
- Consider CloudFront cache settings

## 📱 Mobile support

Aplikácia je **responsive** a funguje na:
- ✅ Desktop browsers
- ✅ Mobile browsers  
- ✅ Tablets
- ✅ Progressive Web App (PWA) ready

## 🎉 Hotovo!

Vaša AI Chat aplikácia je teraz:
- 🌍 **Globálne dostupná**
- 🔒 **Bezpečná** s AWS Cognito
- ⚡ **Rýchla** s CDN
- 🔄 **Automaticky aktualizovaná**
- 📊 **Monitorovaná** v AWS Console

**Zdieľajte URL s kýmkoľvek na svete!** 🚀