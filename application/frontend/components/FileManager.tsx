'use client';

import { useState, useEffect } from 'react';
import { FileText, Download, Calendar, Tag, User, Database, RefreshCw } from 'lucide-react';
import { listUserFiles, createPreselectedUpload, listPreselectedUploads } from '@/lib/s3-manager-client';
import { useUserRole } from '@/hooks/useUserRole';

interface FileInfo {
  key: string;
  filename: string;
  size: number;
  last_modified: string;
  tags?: Record<string, string>;
  metadata?: Record<string, string>;
  content_type?: string;
  timestamp_folder?: string;
}

interface PreselectedUpload {
  upload_id: string;
  expected_filename: string;
  status: string;
  created_at: string;
  expires_at: number;
  used: boolean;
  max_file_size: number;
  allowed_types: string[];
}

export default function FileManager() {
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [preselectedUploads, setPreselectedUploads] = useState<PreselectedUpload[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'files' | 'preselected'>('files');
  const [newPreselectedFilename, setNewPreselectedFilename] = useState('');
  const { canWrite, isAdmin } = useUserRole();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [filesResult, preselectedResult] = await Promise.all([
        listUserFiles(),
        listPreselectedUploads()
      ]);

      if (filesResult.success) {
        setFiles(filesResult.files);
      }

      if (preselectedResult.success) {
        setPreselectedUploads(preselectedResult.uploads);
      }
    } catch (error) {
      console.error('Error loading file data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreatePreselected = async () => {
    if (!newPreselectedFilename.trim()) return;

    try {
      const result = await createPreselectedUpload(
        newPreselectedFilename,
        50 * 1024 * 1024, // 50MB
        undefined, // Allow all types
        24 // 24 hours
      );

      if (result.success) {
        setNewPreselectedFilename('');
        await loadData(); // Refresh data
      } else {
        console.error('Failed to create preselected upload:', result.error);
      }
    } catch (error) {
      console.error('Error creating preselected upload:', error);
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const getS3Path = (file: FileInfo) => {
    const parts = file.key.split('/');
    if (parts.length >= 3) {
      return `${parts[0]}/${parts[1]}/${parts[2]}/...`;
    }
    return file.key;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-gray-900">File Manager</h1>
        <button
          onClick={loadData}
          className="flex items-center gap-2 px-3 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('files')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'files'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center">
              <FileText className="w-4 h-4 mr-2" />
              My Files ({files.length})
            </div>
          </button>
          {canWrite && (
            <button
              onClick={() => setActiveTab('preselected')}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === 'preselected'
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <div className="flex items-center">
                <Database className="w-4 h-4 mr-2" />
                Pre-selected Uploads ({preselectedUploads.length})
              </div>
            </button>
          )}
        </nav>
      </div>

      {/* Files Tab */}
      {activeTab === 'files' && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Your Uploaded Files</h2>
          
          {files.length === 0 ? (
            <div className="text-center py-8">
              <FileText className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No files uploaded yet</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {files.map((file, index) => (
                <div key={index} className="bg-white p-4 rounded-lg border border-gray-200 hover:border-gray-300 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <FileText className="w-5 h-5 text-gray-500" />
                        <h3 className="font-medium text-gray-900">{file.filename}</h3>
                        <span className="text-sm text-gray-500">({formatFileSize(file.size)})</span>
                      </div>
                      
                      <div className="text-sm text-gray-600 space-y-1">
                        <div className="flex items-center gap-2">
                          <Calendar className="w-4 h-4" />
                          <span>Modified: {formatDate(file.last_modified)}</span>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          <Database className="w-4 h-4" />
                          <span className="font-mono text-xs">S3: {getS3Path(file)}</span>
                        </div>

                        {file.tags && Object.keys(file.tags).length > 0 && (
                          <div className="flex items-center gap-2">
                            <Tag className="w-4 h-4" />
                            <div className="flex flex-wrap gap-1">
                              {Object.entries(file.tags).slice(0, 3).map(([key, value]) => (
                                <span key={key} className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded">
                                  {key}: {value}
                                </span>
                              ))}
                              {Object.keys(file.tags).length > 3 && (
                                <span className="text-xs text-gray-500">
                                  +{Object.keys(file.tags).length - 3} more
                                </span>
                              )}
                            </div>
                          </div>
                        )}

                        {file.metadata && file.metadata['uploader-user-id'] && (
                          <div className="flex items-center gap-2">
                            <User className="w-4 h-4" />
                            <span>Uploader: {file.metadata['uploader-user-id']}</span>
                          </div>
                        )}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                        Structured
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Pre-selected Uploads Tab */}
      {activeTab === 'preselected' && canWrite && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Pre-selected Upload Slots</h2>
          
          {/* Create New Pre-selected Upload */}
          <div className="bg-blue-50 p-4 rounded-lg mb-6">
            <h3 className="font-medium text-blue-900 mb-3">Create New Upload Slot</h3>
            <div className="flex gap-3">
              <input
                type="text"
                value={newPreselectedFilename}
                onChange={(e) => setNewPreselectedFilename(e.target.value)}
                placeholder="Expected filename (e.g., report.pdf)"
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleCreatePreselected}
                disabled={!newPreselectedFilename.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                Create Slot
              </button>
            </div>
            <p className="text-sm text-blue-700 mt-2">
              This will create a secure upload slot that expires in 24 hours.
            </p>
          </div>

          {preselectedUploads.length === 0 ? (
            <div className="text-center py-8">
              <Database className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No pre-selected upload slots created yet</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {preselectedUploads.map((upload, index) => (
                <div key={index} className="bg-white p-4 rounded-lg border border-gray-200">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-2">
                        <Database className="w-5 h-5 text-gray-500" />
                        <h3 className="font-medium text-gray-900">{upload.expected_filename}</h3>
                        <span className={`px-2 py-1 text-xs rounded ${
                          upload.status === 'completed' ? 'bg-green-100 text-green-800' :
                          upload.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {upload.status}
                        </span>
                      </div>
                      
                      <div className="text-sm text-gray-600 space-y-1">
                        <div>Created: {formatDate(upload.created_at)}</div>
                        <div>Expires: {formatDate(new Date(upload.expires_at * 1000).toISOString())}</div>
                        <div>Max Size: {formatFileSize(upload.max_file_size)}</div>
                        <div>Types: {upload.allowed_types.join(', ')}</div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-2">
                      {upload.used ? (
                        <span className="px-2 py-1 bg-gray-100 text-gray-800 text-xs rounded">
                          Used
                        </span>
                      ) : (
                        <span className="px-2 py-1 bg-green-100 text-green-800 text-xs rounded">
                          Available
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}