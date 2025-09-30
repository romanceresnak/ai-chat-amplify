import { defineAuth } from '@aws-amplify/backend';

/**
 * Define and configure your auth resource
 * @see https://docs.amplify.aws/gen2/build-a-backend/auth
 */
export const auth = defineAuth({
  loginWith: {
    email: {
      verificationEmailStyle: 'CODE',
      verificationEmailSubject: 'Overte svoj účet pre AI Chat Assistant',
      verificationEmailBody: (createCode) => `Váš overovací kód je ${createCode()}`,
    },
  },
  userAttributes: {
    email: {
      required: true,
      mutable: true,
    },
  },
  accountRecovery: 'EMAIL_ONLY',
  passwordPolicy: {
    minLength: 8,
    requireLowercase: true,
    requireUppercase: true,
    requireNumbers: true,
    requireSymbols: true,
  },
  // Enable MFA as optional
  multifactor: {
    mode: 'OPTIONAL',
    totp: true,
  },
});