import { fetchAuthSession } from 'aws-amplify/auth';

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

export async function callLambdaFunction(functionPath: string, data: any, method: string = 'POST') {
  try {
    const url = new URL(`${API_URL}${functionPath}`);
    
    // Get the current auth session
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    
    const options: RequestInit = {
      method,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': token })
      },
    };

    if (method !== 'GET' && data) {
      options.body = JSON.stringify(data);
    }

    const response = await fetch(url.href, options);

    if (!response.ok) {
      throw new Error(`API call failed: ${response.statusText}`);
    }

    return await response.json();
  } catch (error) {
    console.error('Error calling API:', error);
    throw error;
  }
}

export async function generatePresentation(prompt: string, files: any[] = [], useLangChain: boolean = true) {
  // Multi-agent API call with LangChain support
  const shouldUseLangChain = useLangChain && process.env.NEXT_PUBLIC_USE_LANGCHAIN !== 'false';
  
  return callLambdaFunction('/presentations', {
    instructions: prompt,
    mode: 'modify',
    template_key: 'PUBLIC IP South Plains (1).pptx',
    document_key: 'documents/sample.pdf',
    files: files.map(f => f.key),
    analyze_structure: false,
    use_langchain: shouldUseLangChain
  });
}

export async function listPresentations() {
  return callLambdaFunction('/presentations', null, 'GET');
}

export function isPresentationRequest(message: string): boolean {
  const lowerMessage = message.toLowerCase();
  
  // Check for slide number pattern (e.g., "slide 23:")
  const slideNumberPattern = /slide\s+\d+/i;
  if (slideNumberPattern.test(message)) {
    return true;
  }
  
  // Check for slide-related keywords
  const slideKeywords = ['slide', 'powerpoint', 'ppt', 'presentation'];
  const actionKeywords = ['create', 'generate', 'make', 'design', 'build', 'update', 'modify', 'edit'];
  
  // Check if message contains both slide and action keywords
  const hasSlideKeyword = slideKeywords.some(keyword => lowerMessage.includes(keyword));
  const hasActionKeyword = actionKeywords.some(keyword => lowerMessage.includes(keyword));
  
  return hasSlideKeyword && hasActionKeyword;
}