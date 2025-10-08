# AWS Lambda Environment Variables Setup Guide

This guide shows you how to add environment variables (TAVILY_API_KEY, SERPAPI_API_KEY, USE_LANGCHAIN) to your AWS Lambda function.

## Step 1: Access AWS Lambda Console

1. Log in to AWS Management Console
2. Navigate to Lambda service (search "Lambda" in the search bar)

```
┌─────────────────────────────────────────────────────────────┐
│ AWS Management Console                                      │
├─────────────────────────────────────────────────────────────┤
│ 🔍 Search: Lambda                                           │
│                                                             │
│ Services:                                                   │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ 🔧 Lambda - Run code without thinking about servers     ││
│ └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Step 2: Select Your Lambda Function

Click on your Lambda function from the functions list.

```
┌─────────────────────────────────────────────────────────────┐
│ Lambda > Functions                                          │
├─────────────────────────────────────────────────────────────┤
│ Functions (1)                                               │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ Function name              Status    Runtime            ││
│ │ ─────────────────────────────────────────────────────  ││
│ │ 📦 your-function-name      ✅ Active  Python 3.x       ││
│ │    ↑ Click here                                        ││
│ └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Step 3: Navigate to Configuration Tab

After selecting your function, click on the "Configuration" tab.

```
┌─────────────────────────────────────────────────────────────┐
│ your-function-name                                          │
├─────────────────────────────────────────────────────────────┤
│ Code  Test  Monitor  [Configuration]  Aliases  Versions    │
│                          ↑                                  │
│                     Click here                              │
└─────────────────────────────────────────────────────────────┘
```

## Step 4: Select Environment Variables

In the Configuration tab, click on "Environment variables" from the left sidebar.

```
┌─────────────────────────────────────────────────────────────┐
│ Configuration                                               │
├─────────────────────────────────────────────────────────────┤
│ Left Sidebar:              │ Main Panel:                   │
│ ┌─────────────────────┐   │                               │
│ │ General configuration │   │                               │
│ │ Triggers             │   │                               │
│ │ Permissions          │   │                               │
│ │ [Environment variables] ← │ Environment variables        │
│ │ VPC                  │   │                               │
│ │ Monitoring tools     │   │                               │
│ └─────────────────────┐   │                               │
└─────────────────────────────────────────────────────────────┘
```

## Step 5: Add Environment Variables

Click the "Edit" button to add new environment variables.

```
┌─────────────────────────────────────────────────────────────┐
│ Environment variables                                       │
├─────────────────────────────────────────────────────────────┤
│                                           [Edit] ← Click    │
│                                                             │
│ Environment variables (0)                                   │
│ No environment variables                                    │
└─────────────────────────────────────────────────────────────┘
```

## Step 6: Add Your API Keys

Click "Add environment variable" for each key you need to add.

```
┌─────────────────────────────────────────────────────────────┐
│ Edit environment variables                                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ Environment variables                                       │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ Key                    │ Value                          ││
│ │ ──────────────────────┼────────────────────────────────││
│ │ TAVILY_API_KEY        │ your-tavily-api-key-here       ││
│ │ SERPAPI_API_KEY       │ your-serpapi-key-here          ││
│ │ USE_LANGCHAIN         │ true                           ││
│ └─────────────────────────────────────────────────────────┘│
│                                                             │
│ [+ Add environment variable]                                │
│                                                             │
│ [Cancel]                                    [Save]          │
└─────────────────────────────────────────────────────────────┘
```

### Required Environment Variables:

1. **TAVILY_API_KEY**: Your Tavily API key for web search
   - Get it from: https://app.tavily.com/
   
2. **SERPAPI_API_KEY**: Your SerpAPI key for search results
   - Get it from: https://serpapi.com/
   
3. **USE_LANGCHAIN**: Set to "true" to enable LangChain integration
   - Value: `true` or `false`

## Step 7: Save Your Changes

Click the "Save" button at the bottom right to apply your environment variables.

## Quick Reference

### Navigation Path:
```
AWS Console → Lambda → Functions → [Your Function] → Configuration → Environment variables → Edit
```

### Environment Variables to Add:
```
TAVILY_API_KEY     = your-tavily-api-key
SERPAPI_API_KEY    = your-serpapi-key
USE_LANGCHAIN      = true
```

## Verification

After saving, your environment variables should appear like this:

```
┌─────────────────────────────────────────────────────────────┐
│ Environment variables                                       │
├─────────────────────────────────────────────────────────────┤
│                                                    [Edit]   │
│                                                             │
│ Environment variables (3)                                   │
│ ┌─────────────────────────────────────────────────────────┐│
│ │ Key                    │ Value                          ││
│ │ ──────────────────────┼────────────────────────────────││
│ │ TAVILY_API_KEY        │ ••••••••••••                   ││
│ │ SERPAPI_API_KEY       │ ••••••••••••                   ││
│ │ USE_LANGCHAIN         │ true                           ││
│ └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Important Notes

- Environment variables are encrypted at rest
- Changes take effect immediately after saving
- No function redeployment needed
- Values are hidden (shown as dots) for security
- Make sure to keep your API keys secure and never commit them to version control

## Troubleshooting

If your Lambda function can't access the environment variables:
1. Ensure you clicked "Save" after adding them
2. Check that the key names match exactly (case-sensitive)
3. Verify the function has the necessary permissions
4. Check CloudWatch logs for any errors

---

**Quick Tip**: You can also set these via AWS CLI:
```bash
aws lambda update-function-configuration \
    --function-name your-function-name \
    --environment Variables={TAVILY_API_KEY=your-key,SERPAPI_API_KEY=your-key,USE_LANGCHAIN=true}
```