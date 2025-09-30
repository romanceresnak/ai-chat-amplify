'use client';

import { useState, useRef, useEffect } from 'react';
import { BedrockRuntimeClient, InvokeModelCommand } from '@aws-sdk/client-bedrock-runtime';
import { fetchAuthSession } from 'aws-amplify/auth';
import { uploadData } from 'aws-amplify/storage';
import { generateClient } from 'aws-amplify/data';
import { useDropzone } from 'react-dropzone';
import { Send, Upload, X, FileText, Loader2 } from 'lucide-react';
import type { Schema } from '@/amplify/data/resource';

const client = generateClient<Schema>();

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  files?: string[];
}

interface UploadedFile {
  name: string;
  key: string;
  size: number;
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [bedrockClient, setBedrockClient] = useState<BedrockRuntimeClient | null>(null);

  useEffect(() => {
    initializeBedrockClient();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const initializeBedrockClient = async () => {
    try {
      const session = await fetchAuthSession();
      const client = new BedrockRuntimeClient({
        region: 'us-east-1', // Zmeňte podľa vášho regiónu
        credentials: session.credentials,
      });
      setBedrockClient(client);
    } catch (error) {
      console.error('Error initializing Bedrock client:', error);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const onDrop = async (acceptedFiles: File[]) => {
    setIsUploading(true);
    const newFiles: UploadedFile[] = [];

    for (const file of acceptedFiles) {
      try {
        const key = `chat-files/${Date.now()}-${file.name}`;
        const result = await uploadData({
          key,
          data: file,
          options: {
            contentType: file.type,
          }
        }).result;

        newFiles.push({
          name: file.name,
          key: result.key,
          size: file.size,
        });
      } catch (error) {
        console.error('Error uploading file:', error);
      }
    }

    setUploadedFiles([...uploadedFiles, ...newFiles]);
    setIsUploading(false);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': [],
      'application/pdf': [],
      'text/*': [],
      'application/msword': [],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [],
    },
  });

  const removeFile = (index: number) => {
    const newFiles = [...uploadedFiles];
    newFiles.splice(index, 1);
    setUploadedFiles(newFiles);
  };

  const sendMessage = async () => {
    if (!input.trim() && uploadedFiles.length === 0) return;
    if (!bedrockClient) {
      console.error('Bedrock client not initialized');
      return;
    }

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
      files: uploadedFiles.map(f => f.key),
    };

    setMessages([...messages, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Save user message to database
      await client.models.ChatMessage.create({
        content: userMessage.content,
        role: 'user',
        timestamp: userMessage.timestamp.toISOString(),
        userId: 'current-user', // Get from auth context
        files: userMessage.files,
      });

      // Prepare prompt for Bedrock
      let prompt = userMessage.content;
      if (uploadedFiles.length > 0) {
        prompt += `\\n\\nPriložené súbory: ${uploadedFiles.map(f => f.name).join(', ')}`;
      }

      // Call Bedrock Claude model
      const command = new InvokeModelCommand({
        modelId: 'anthropic.claude-3-5-sonnet-20241022-v2:0',
        body: JSON.stringify({
          anthropic_version: 'bedrock-2023-05-31',
          max_tokens: 4096,
          messages: [
            {
              role: 'user',
              content: prompt,
            },
          ],
        }),
        contentType: 'application/json',
      });

      const response = await bedrockClient.send(command);
      const responseData = JSON.parse(new TextDecoder().decode(response.body));
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: responseData.content[0].text,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Save assistant message to database
      await client.models.ChatMessage.create({
        content: assistantMessage.content,
        role: 'assistant',
        timestamp: assistantMessage.timestamp.toISOString(),
        userId: 'current-user',
      });

      // Clear uploaded files after sending
      setUploadedFiles([]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Prepáčte, vyskytla sa chyba pri spracovaní vašej požiadavky.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-20">
            <h2 className="text-xl font-semibold mb-2">Vitajte v AI Chat Assistant</h2>
            <p>Začnite konverzáciu zadaním správy alebo nahraním súboru</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[70%] rounded-lg p-4 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border border-gray-200'
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                {message.files && message.files.length > 0 && (
                  <div className="mt-2 text-sm opacity-75">
                    <FileText className="inline w-4 h-4 mr-1" />
                    {message.files.length} súbor(ov) priložených
                  </div>
                )}
                <p className={`text-xs mt-2 ${
                  message.role === 'user' ? 'text-blue-100' : 'text-gray-500'
                }`}>
                  {message.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))
        )}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-lg p-4">
              <Loader2 className="w-5 h-5 animate-spin" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="border-t bg-white p-4">
        {uploadedFiles.length > 0 && (
          <div className="mb-3 p-3 bg-gray-100 rounded-lg">
            <p className="text-sm font-medium text-gray-700 mb-2">Priložené súbory:</p>
            <div className="space-y-1">
              {uploadedFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-gray-500" />
                    {file.name} ({(file.size / 1024).toFixed(1)} KB)
                  </span>
                  <button
                    onClick={() => removeFile(index)}
                    className="text-red-500 hover:text-red-700"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-2">
          <div
            {...getRootProps()}
            className={`p-2 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${
              isDragActive ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
            } ${isUploading ? 'opacity-50' : ''}`}
          >
            <input {...getInputProps()} />
            {isUploading ? (
              <Loader2 className="w-5 h-5 text-gray-500 animate-spin" />
            ) : (
              <Upload className="w-5 h-5 text-gray-500" />
            )}
          </div>

          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
            placeholder="Napíšte správu..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />

          <button
            onClick={sendMessage}
            disabled={isLoading || (!input.trim() && uploadedFiles.length === 0)}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}