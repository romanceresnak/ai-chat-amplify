const API_URL = process.env.NEXT_PUBLIC_API_URL || '';

export async function callLambdaFunction(functionPath: string, data: any) {
  try {
    const url = new URL(`${API_URL}${functionPath}`);
    const body = JSON.stringify(data);

    const response = await fetch(url.href, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
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