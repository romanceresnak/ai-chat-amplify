import { a, defineData, type ClientSchema } from '@aws-amplify/backend';

const schema = a.schema({
  ChatMessage: a.model({
    id: a.id().required(),
    content: a.string().required(),
    role: a.enum(['user', 'assistant']),
    timestamp: a.datetime().required(),
    userId: a.string().required(),
    files: a.string().array(),
    conversationId: a.string(),
  })
  .authorization(allow => [
    allow.owner().identityClaim('sub'),
  ]),

  Conversation: a.model({
    id: a.id().required(),
    title: a.string().required(),
    userId: a.string().required(),
    createdAt: a.datetime().required(),
    updatedAt: a.datetime(),
    messages: a.hasMany('ChatMessage', 'conversationId'),
  })
  .authorization(allow => [
    allow.owner().identityClaim('sub'),
  ]),
});

export type Schema = ClientSchema<typeof schema>;

export const data = defineData({
  schema,
  authorizationModes: {
    defaultAuthorizationMode: 'userPool',
  },
});