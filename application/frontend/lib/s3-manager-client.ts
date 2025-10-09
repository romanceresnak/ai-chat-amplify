import { fetchAuthSession, getCurrentUser } from 'aws-amplify/auth';

const S3_MANAGER_URL = process.env.NEXT_PUBLIC_S3_MANAGER_URL || `${process.env.NEXT_PUBLIC_API_URL}/s3-manager`;

interface UploadResult {
  success: boolean;
  file_info?: {
    s3_key: string;
    bucket: string;
    original_filename: string;
    versioned: boolean;
    user_id: string;
    client_system_id: string;
    upload_timestamp: string;
    file_size: number;
    content_type: string;
    tags: Array<{Key: string; Value: string}>;
    metadata: Record<string, string>;
  };
  error?: string;
  message?: string;
}

interface PreselectedUploadResult {
  success: boolean;
  upload_id?: string;
  presigned_url?: string;
  expected_s3_key?: string;
  max_file_size?: number;
  allowed_types?: string[];
  expires_at?: string;
  instructions?: {
    method: string;
    url: string;
    headers: Record<string, string>;
  };
  error?: string;
}

interface FileListResult {
  success: boolean;
  files: Array<{
    key: string;
    filename: string;
    size: number;
    last_modified: string;
    tags?: Record<string, string>;
    metadata?: Record<string, string>;
    content_type?: string;
    timestamp_folder?: string;
  }>;
  total_files: number;
  user_id: string;
  client_system_id: string;
  error?: string;
}

async function callS3Manager(operation: string, data: any): Promise<any> {
  try {
    // Get authentication token
    const session = await fetchAuthSession();
    const token = session.tokens?.idToken?.toString();
    
    const response = await fetch(S3_MANAGER_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': token })
      },
      body: JSON.stringify({
        operation,
        ...data
      })
    });

    if (!response.ok) {
      throw new Error(`S3 Manager API call failed: ${response.statusText}`);
    }

    const result = await response.json();
    return result;
  } catch (error) {
    console.error('Error calling S3 Manager:', error);
    throw error;
  }
}

export async function uploadFileWithStructure(
  file: File,
  clientSystemId?: string,
  metadata?: Record<string, string>
): Promise<UploadResult> {
  try {
    // Get current user
    const user = await getCurrentUser();
    const userId = user.userId || user.username || 'anonymous';

    // Convert file to base64
    const fileBuffer = await file.arrayBuffer();
    const fileBase64 = btoa(
      new Uint8Array(fileBuffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
    );

    const result = await callS3Manager('upload', {
      user_id: userId,
      filename: file.name,
      file_content: fileBase64,
      file_size: file.size,
      content_type: file.type,
      client_system_id: clientSystemId,
      metadata: {
        original_name: file.name,
        upload_source: 'chat_interface',
        ...metadata
      }
    });

    return result;
  } catch (error) {
    console.error('Error uploading file with structure:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Upload failed'
    };
  }
}

export async function createPreselectedUpload(
  expectedFilename: string,
  maxFileSize: number = 50 * 1024 * 1024, // 50MB
  allowedTypes?: string[],
  expiresInHours: number = 24,
  clientSystemId?: string
): Promise<PreselectedUploadResult> {
  try {
    // Get current user
    const user = await getCurrentUser();
    const userId = user.userId || user.username || 'anonymous';

    const result = await callS3Manager('create_preselected', {
      user_id: userId,
      expected_filename: expectedFilename,
      max_file_size: maxFileSize,
      allowed_types: allowedTypes,
      expires_in_hours: expiresInHours,
      client_system_id: clientSystemId
    });

    return result;
  } catch (error) {
    console.error('Error creating preselected upload:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Failed to create preselected upload'
    };
  }
}

export async function validatePreselectedUpload(
  uploadId: string,
  actualFilename: string,
  fileSize: number
): Promise<{success: boolean; preselected_info?: any; message?: string; error?: string}> {
  try {
    const result = await callS3Manager('validate_preselected', {
      upload_id: uploadId,
      actual_filename: actualFilename,
      file_size: fileSize
    });

    return result;
  } catch (error) {
    console.error('Error validating preselected upload:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Validation failed'
    };
  }
}

export async function listUserFiles(
  clientSystemId?: string,
  limit: number = 100
): Promise<FileListResult> {
  try {
    // Get current user
    const user = await getCurrentUser();
    const userId = user.userId || user.username || 'anonymous';

    const result = await callS3Manager('list', {
      user_id: userId,
      client_system_id: clientSystemId,
      limit
    });

    return result;
  } catch (error) {
    console.error('Error listing user files:', error);
    return {
      success: false,
      files: [],
      total_files: 0,
      user_id: '',
      client_system_id: '',
      error: error instanceof Error ? error.message : 'Failed to list files'
    };
  }
}

export async function listPreselectedUploads(
  clientSystemId?: string
): Promise<{success: boolean; uploads: any[]; total: number; error?: string}> {
  try {
    // Get current user
    const user = await getCurrentUser();
    const userId = user.userId || user.username || 'anonymous';

    const result = await callS3Manager('list_preselected', {
      user_id: userId,
      client_system_id: clientSystemId
    });

    return result;
  } catch (error) {
    console.error('Error listing preselected uploads:', error);
    return {
      success: false,
      uploads: [],
      total: 0,
      error: error instanceof Error ? error.message : 'Failed to list preselected uploads'
    };
  }
}

export async function uploadViaPresignedUrl(
  presignedUrl: string,
  file: File,
  headers?: Record<string, string>
): Promise<{success: boolean; error?: string}> {
  try {
    const response = await fetch(presignedUrl, {
      method: 'PUT',
      body: file,
      headers: {
        'Content-Type': file.type,
        ...headers
      }
    });

    if (!response.ok) {
      throw new Error(`Upload failed: ${response.statusText}`);
    }

    return { success: true };
  } catch (error) {
    console.error('Error uploading via presigned URL:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Upload failed'
    };
  }
}