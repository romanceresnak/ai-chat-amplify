import { fetchAuthSession } from 'aws-amplify/auth';
import * as aws4 from 'aws4';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
const AWS_REGION = process.env.NEXT_PUBLIC_AWS_REGION || 'eu-west-1';

export async function callLambdaFunction(functionPath: string, data: any) {
  try {
    const session = await fetchAuthSession();
    const credentials = session.credentials;

    if (!credentials) {
      throw new Error('No AWS credentials available');
    }

    const url = new URL(`${API_URL}${functionPath}`);
    const body = JSON.stringify(data);

    // Prepare request for AWS4 signing
    const request = {
      host: url.hostname,
      method: 'POST',
      url: url.href,
      path: url.pathname + url.search,
      headers: {
        'Content-Type': 'application/json',
      },
      body,
      service: 'execute-api',
      region: AWS_REGION,
    };

    // Sign the request with AWS credentials
    const awsCredentials: any = {
      accessKeyId: credentials.accessKeyId,
      secretAccessKey: credentials.secretAccessKey,
    };
    
    if (credentials.sessionToken) {
      awsCredentials.sessionToken = credentials.sessionToken;
    }
    
    const signedRequest = aws4.sign(request, awsCredentials);

    const response = await fetch(url.href, {
      method: 'POST',
      headers: signedRequest.headers as HeadersInit,
      body,
    });

    if (!response.ok) {
      throw new Error(`API call failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error calling API:', error);
    throw error;
  }
}

export async function generatePresentation(prompt: string) {
  // Parse the prompt to extract template and instructions
  const templateMatch = prompt.match(/template[:\s]+(\w+)/i);
  const template = templateMatch ? templateMatch[1] : 'default';
  
  return callLambdaFunction('/presentations', {
    instructions: prompt,
    template_key: `templates/${template}.pptx`,
    document_key: 'documents/sample.pdf', // This should be dynamic based on uploaded files
  });
}

export function isPresentationRequest(message: string): boolean {
  const lowerMessage = message.toLowerCase();
  
  // Check for slide-related keywords
  const slideKeywords = ['slide', 'powerpoint', 'ppt', 'presentation'];
  const actionKeywords = ['create', 'generate', 'make', 'design', 'build'];
  
  // Check if message contains both slide and action keywords
  const hasSlideKeyword = slideKeywords.some(keyword => lowerMessage.includes(keyword));
  const hasActionKeyword = actionKeywords.some(keyword => lowerMessage.includes(keyword));
  
  return hasSlideKeyword && hasActionKeyword;
}