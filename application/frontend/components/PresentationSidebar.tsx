'use client';

import { useState, useEffect } from 'react';
import { Download, FileText, Calendar, Loader2 } from 'lucide-react';
import { listPresentations } from '@/lib/api-client';

interface Presentation {
  id: string;
  name: string;
  key: string;
  created: string;
  size: number;
  download_url: string;
}

export default function PresentationSidebar() {
  const [presentations, setPresentations] = useState<Presentation[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadPresentations();
  }, []);

  const loadPresentations = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await listPresentations();
      setPresentations(response.presentations || []);
    } catch (error) {
      console.error('Error loading presentations:', error);
      setError('Failed to load presentations');
    } finally {
      setIsLoading(false);
    }
  };

  const downloadPresentation = (downloadUrl: string, fileName: string) => {
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <div className="w-80 bg-white border-r border-gray-200 flex flex-col h-full">
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">Presentations</h2>
          <button
            onClick={loadPresentations}
            className="p-1 text-gray-500 hover:text-gray-700 rounded"
            disabled={isLoading}
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <span className="text-sm">Refresh</span>
            )}
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {isLoading ? (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="w-6 h-6 animate-spin text-gray-500" />
          </div>
        ) : error ? (
          <div className="p-4 text-center">
            <p className="text-red-500 text-sm">{error}</p>
            <button
              onClick={loadPresentations}
              className="mt-2 text-blue-600 hover:text-blue-800 text-sm"
            >
              Try again
            </button>
          </div>
        ) : presentations.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <FileText className="w-12 h-12 mx-auto mb-2 text-gray-300" />
            <p className="text-sm">No presentations yet</p>
            <p className="text-xs text-gray-400 mt-1">
              Create your first presentation by chatting about slides or PowerPoint
            </p>
          </div>
        ) : (
          <div className="p-2 space-y-2">
            {presentations.map((presentation) => (
              <div
                key={presentation.key}
                className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <FileText className="w-4 h-4 text-blue-600 flex-shrink-0" />
                      <h3 className="text-sm font-medium text-gray-900 truncate">
                        {presentation.name}
                      </h3>
                    </div>
                    
                    <div className="flex items-center gap-3 text-xs text-gray-500 mb-2">
                      <div className="flex items-center gap-1">
                        <Calendar className="w-3 h-3" />
                        {formatDate(presentation.created)}
                      </div>
                      <span>{formatFileSize(presentation.size)}</span>
                    </div>
                  </div>
                  
                  <button
                    onClick={() => downloadPresentation(presentation.download_url, presentation.name)}
                    className="ml-2 p-1 text-gray-500 hover:text-blue-600 rounded transition-colors"
                    title="Download presentation"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}