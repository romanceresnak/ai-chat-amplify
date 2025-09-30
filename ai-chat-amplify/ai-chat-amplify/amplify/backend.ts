import { defineBackend } from '@aws-amplify/backend';
import { auth } from './auth/resource';
import { data } from './data/resource';
import { storage } from './storage/resource';
import { Stack } from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';

/**
 * @see https://docs.amplify.aws/react/build-a-backend/ to add storage, functions, and more
 */
const backend = defineBackend({
  auth,
  data,
  storage,
});

// Create a new stack for custom resources
const customResourceStack = backend.createStack('custom-resources-stack');

// Add Bedrock permissions to authenticated role
const authenticatedRole = backend.auth.resources.authenticatedUserIamRole;

// Add Bedrock policy
authenticatedRole.addToPolicy(
  new iam.PolicyStatement({
    effect: iam.Effect.ALLOW,
    actions: [
      'bedrock:InvokeModel',
      'bedrock:InvokeModelWithResponseStream',
    ],
    resources: [
      `arn:aws:bedrock:*:*:inference-profile/*`,
      `arn:aws:bedrock:*::foundation-model/*`,
    ],
  })
);

// Add permissions for Knowledge Base if needed
authenticatedRole.addToPolicy(
  new iam.PolicyStatement({
    effect: iam.Effect.ALLOW,
    actions: [
      'bedrock:Retrieve',
      'bedrock:RetrieveAndGenerate',
    ],
    resources: ['*'],
  })
);