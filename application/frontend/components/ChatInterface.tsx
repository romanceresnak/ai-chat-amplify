'use client';

import { useState, useRef, useEffect } from 'react';
// Bedrock removed - using mock responses only
import { fetchAuthSession } from 'aws-amplify/auth';
import { uploadData } from 'aws-amplify/storage';
import { useDropzone } from 'react-dropzone';
import { Send, Upload, X, FileText, Loader2, Lock } from 'lucide-react';
import { isPresentationRequest, generatePresentation } from '@/lib/api-client';
import { getCurrentUser } from 'aws-amplify/auth';
import { useUserRole } from '@/hooks/useUserRole';
import { uploadFileWithStructure } from '@/lib/s3-manager-client';

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
  kbSynced?: boolean; // Knowledge base sync status
  structured?: boolean; // Uses new structured S3 storage
  versioned?: boolean; // File was versioned to avoid conflicts
  systemId?: string; // Client system ID
  uploadTimestamp?: string; // Upload timestamp
}

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [useLangChain, setUseLangChain] = useState(true); // Default to true for web search
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { canRead, canWrite, isAdmin, role } = useUserRole();

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    // Load LangChain preference from localStorage
    const savedPreference = localStorage.getItem('use_langchain');
    if (savedPreference !== null) {
      setUseLangChain(savedPreference === 'true');
    }
  }, []);

  useEffect(() => {
    // Save LangChain preference to localStorage
    localStorage.setItem('use_langchain', useLangChain.toString());
  }, [useLangChain]);

  // Bedrock client initialization removed

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const onDrop = async (acceptedFiles: File[]) => {
    setIsUploading(true);
    const newFiles: UploadedFile[] = [];

    // Get current user for audit logging
    let userId = 'anonymous';
    try {
      const user = await getCurrentUser();
      userId = user.userId || user.username || 'anonymous';
    } catch (error) {
      console.warn('Could not get current user for audit logging:', error);
    }

    for (const file of acceptedFiles) {
      try {
        console.log(`🔄 Uploading file with S3 Manager: ${file.name}`);
        
        // Upload using new S3 manager with structured storage and tagging
        const uploadResult = await uploadFileWithStructure(
          file,
          process.env.NEXT_PUBLIC_CLIENT_SYSTEM_ID || 'scribbe-ai-system',
          {
            upload_source: 'chat_interface',
            user_session: userId,
            upload_timestamp: new Date().toISOString()
          }
        );

        if (uploadResult.success && uploadResult.file_info) {
          const fileInfo = uploadResult.file_info;
          console.log(`✅ File uploaded successfully: ${fileInfo.s3_key}`);
          
          // Log successful upload audit event
          await logAuditEvent({
            eventType: 'file_upload',
            userId: userId,
            action: 'UPLOAD_FILE_STRUCTURED',
            resource: fileInfo.s3_key,
            details: {
              original_filename: file.name,
              s3_key: fileInfo.s3_key,
              bucket: fileInfo.bucket,
              file_size: file.size,
              file_type: file.type,
              versioned: fileInfo.versioned,
              client_system_id: fileInfo.client_system_id,
              tags: fileInfo.tags,
              structured_storage: true,
              upload_timestamp: fileInfo.upload_timestamp
            }
          });

          newFiles.push({
            name: fileInfo.original_filename,
            key: fileInfo.s3_key,
            size: fileInfo.file_size,
            kbSynced: true, // New S3 manager automatically handles KB sync
            structured: true,
            versioned: fileInfo.versioned,
            systemId: fileInfo.client_system_id,
            uploadTimestamp: fileInfo.upload_timestamp
          });
        } else {
          console.error('❌ Upload failed:', uploadResult.error);
          
          // Log failed upload audit event
          await logAuditEvent({
            eventType: 'file_upload',
            userId: userId,
            action: 'UPLOAD_FILE_FAILED',
            resource: file.name,
            details: {
              filename: file.name,
              file_size: file.size,
              file_type: file.type,
              error: uploadResult.error || 'Unknown error',
              structured_storage: false
            }
          });
        }
      } catch (error) {
        console.error('Error uploading file:', error);
        
        // Log audit trail for upload error
        await logAuditEvent({
          eventType: 'file_upload',
          userId: userId,
          action: 'UPLOAD_FILE_ERROR',
          resource: file.name,
          details: {
            fileName: file.name,
            fileSize: file.size,
            fileType: file.type,
            error: error instanceof Error ? error.message : 'Upload failed'
          }
        });
      }
    }

    setUploadedFiles([...uploadedFiles, ...newFiles]);
    setIsUploading(false);
  };

  // Helper function to log audit events
  const logAuditEvent = async (auditData: any) => {
    try {
      // Call the orchestrator with audit event data
      // The orchestrator will forward this to the audit logger Lambda
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/audit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token && { 'Authorization': token })
        },
        body: JSON.stringify({
          ...auditData,
          timestamp: new Date().toISOString(),
          ipAddress: window.location.hostname, // In production, get real IP
          userAgent: navigator.userAgent
        })
      });
      
      if (!response.ok) {
        console.warn('Failed to log audit event:', response.statusText);
      }
    } catch (error) {
      console.warn('Error logging audit event:', error);
    }
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'image/*': [],
      'application/pdf': [],
      'text/plain': [],
      'text/csv': [],
      'application/json': [],
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
      // Check if this is a presentation generation request
      console.log('Checking if presentation request:', userMessage.content);
      console.log('Is presentation request?', isPresentationRequest(userMessage.content));
      console.log('API URL:', process.env.NEXT_PUBLIC_API_URL);
      
      // Always call the multi-agent API
      const result = await generatePresentation(userMessage.content, uploadedFiles, useLangChain);
      
      // Format the response based on which agent handled it
      let responseContent = result.message || '';
      
      // Add agent-specific formatting
      if (result.agent === 'presentation' && result.presentation_name) {
        responseContent += `\n\n📊 **Presentation Ready**: ${result.presentation_name}`;
        if (result.download_url) {
          responseContent += `\n[Download Now](${result.download_url})`;
        }
      } else if (result.agent === 'document') {
        responseContent = `📄 **Document Analysis**\n\n${responseContent}`;
        if (result.files_analyzed) {
          responseContent += `\n\n*Analyzed ${result.files_analyzed} file(s)*`;
        }
      } else if (result.agent === 'chat') {
        responseContent = `💬 ${responseContent}`;
      } else if (result.agent === 'simple-orchestrator') {
        // LangChain orchestrator response - already formatted
        if (result.tools_used && result.tools_used.length > 0) {
          responseContent += `\n\n*Tools used: ${result.tools_used.join(', ')}*`;
        }
      } else if (result.agent === 'langchain-orchestrator') {
        // Full LangChain orchestrator response
        if (result.tools_used && result.tools_used.length > 0) {
          responseContent += `\n\n*AI Tools: ${result.tools_used.join(', ')}*`;
        }
      }
      
      // Add routing info in dev mode
      if (process.env.NODE_ENV === 'development') {
        responseContent += `\n\n*[Routed to: ${result.routed_to || 'unknown'} agent]*`;
      }
      
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: responseContent,
        timestamp: new Date(),
      };
      
      setMessages(prev => [...prev, assistantMessage]);

      // Clear uploaded files after sending
      setUploadedFiles([]);
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: 'Sorry, an error occurred while processing your request. Please make sure you have access to AWS Bedrock Claude models in the eu-west-1 region.',
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-20">
            <h2 className="text-xl font-semibold mb-2">Welcome to AI Chat Assistant</h2>
            <p>Start a conversation by typing a message or uploading a file</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-md rounded-lg p-4 ${
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white border border-gray-200'
                }`}
              >
                <p className="whitespace-pre-wrap break-words leading-relaxed">{message.content}</p>
                {message.files && message.files.length > 0 && (
                  <div className="mt-2 text-sm opacity-75">
                    <FileText className="inline w-4 h-4 mr-1" />
                    {message.files.length} file(s) attached
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
        {role && (
          <div className="mb-2 text-xs text-gray-500">
            Current role: <span className="font-medium">{role}</span>
          </div>
        )}
        {uploadedFiles.length > 0 && (
          <div className="mb-3 p-3 bg-gray-100 rounded-lg">
            <p className="text-sm font-medium text-gray-700 mb-2">Attached files:</p>
            <div className="space-y-1">
              {uploadedFiles.map((file, index) => (
                <div key={index} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-2">
                    <FileText className="w-4 h-4 text-gray-500" />
                    <span className="flex items-center gap-1">
                      {file.name} ({(file.size / 1024).toFixed(1)} KB)
                      {file.structured ? (
                        <span className="text-blue-600 text-xs" title="Structured S3 Storage">🏗️</span>
                      ) : null}
                      {file.versioned ? (
                        <span className="text-purple-600 text-xs" title="Versioned File">🔄</span>
                      ) : null}
                      {file.kbSynced ? (
                        <span className="text-green-600 text-xs" title="Added to Knowledge Base">📚</span>
                      ) : (
                        <span className="text-gray-400 text-xs" title="Not in Knowledge Base">📄</span>
                      )}
                      {file.systemId && (
                        <span className="text-xs text-gray-500" title={`System: ${file.systemId}`}>
                          [{file.systemId.split('-').pop()}]
                        </span>
                      )}
                    </span>
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

        {/* LangChain Toggle */}
        <div className="mb-3 flex items-center gap-3 text-sm">
          <span className="text-gray-600">AI Mode:</span>
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={useLangChain}
              onChange={(e) => setUseLangChain(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className={useLangChain ? 'text-blue-600 font-medium' : 'text-gray-500'}>
              {useLangChain ? '🌐 Advanced AI (Web Search)' : '💬 Basic Chat'}
            </span>
          </label>
        </div>

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
            placeholder="Type a message..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={isLoading}
          />

          <button
            onClick={sendMessage}
            disabled={isLoading || (!input.trim() && uploadedFiles.length === 0)}
            className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            title=""
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