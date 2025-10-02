import { fetchAuthSession } from 'aws-amplify/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

export async function callLambdaFunction(functionPath: string, data: any) {
  try {
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();

    const response = await fetch(`${API_URL}${functionPath}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(data),
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
  
  return callLambdaFunction('/orchestrator', {
    instructions: prompt,
    template_key: `templates/${template}.pptx`,
    document_key: 'documents/sample.pdf', // This should be dynamic based on uploaded files
  });
}

export function isPresentationRequest(message: string): boolean {
  const keywords = [
    'create presentation',
    'generate presentation',
    'make presentation',
    'create slide',
    'generate slide',
    'make slide',
    'powerpoint',
    'ppt',
    'presentation about',
    'slide about'
  ];
  
  const lowerMessage = message.toLowerCase();
  return keywords.some(keyword => lowerMessage.includes(keyword));
}