import { defineStorage } from '@aws-amplify/backend';

export const storage = defineStorage({
  name: 'aiChatStorage',
  access: (allow) => ({
    'media/*': [
      allow.authenticated.to(['read', 'write', 'delete']),
    ],
    'chat-files/*': [
      allow.authenticated.to(['read', 'write']),
      allow.guest.to(['read'])
    ],
  })
});