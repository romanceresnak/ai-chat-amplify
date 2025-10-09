'use client';

import { useState, useEffect } from 'react';
import { Check, X, Eye, Clock, AlertTriangle, User, Calendar, FileText, Shield, TrendingUp } from 'lucide-react';
import { useUserRole } from '@/hooks/useUserRole';
import { useRouter } from 'next/navigation';

interface PendingFile {
  file_id: string;
  file_name: string;
  file_size: number;
  file_type: string;
  uploaded_by: string;
  uploaded_at: string;
  status: 'pending_approval' | 'approved' | 'rejected';
  needs_approval: boolean;
  flagged_reasons: string[];
  s3_key: string;
}

interface AuditLogEntry {
  log_id: string;
  timestamp: string;
  user_id: string;
  action: string;
  resource: string;
  event_type: string;
  details: any;
}

interface PatternInsights {
  total_patterns: number;
  pattern_types: Record<string, number>;
  average_confidence: number;
  top_insights: Array<{
    description: string;
    details: string;
    confidence: number;
    type: string;
  }>;
  recommendations: string[];
}

export default function AdminPanel() {
  const [pendingFiles, setPendingFiles] = useState<PendingFile[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLogEntry[]>([]);
  const [patternInsights, setPatternInsights] = useState<PatternInsights | null>(null);
  const [activeTab, setActiveTab] = useState<'approvals' | 'audit' | 'patterns'>('approvals');
  const [isLoading, setIsLoading] = useState(true);
  const { isAdmin, hasPermission, isLoading: roleLoading } = useUserRole();
  const router = useRouter();

  useEffect(() => {
    if (!roleLoading && !isAdmin) {
      router.push('/');
    }
  }, [isAdmin, roleLoading, router]);

  useEffect(() => {
    if (isAdmin) {
      fetchPendingFiles();
      fetchAuditLogs();
      fetchPatternInsights();
    }
  }, [isAdmin]);

  const fetchPendingFiles = async () => {
    try {
      const response = await fetch('/api/admin/pending-files');
      if (response.ok) {
        const files = await response.json();
        setPendingFiles(files);
      }
    } catch (error) {
      console.error('Error fetching pending files:', error);
    }
  };

  const fetchAuditLogs = async () => {
    try {
      const response = await fetch('/api/admin/audit-logs?limit=50');
      if (response.ok) {
        const logs = await response.json();
        setAuditLogs(logs);
      }
    } catch (error) {
      console.error('Error fetching audit logs:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchPatternInsights = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/patterns`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        }
      });
      if (response.ok) {
        const data = await response.json();
        setPatternInsights(data.insights);
      }
    } catch (error) {
      console.error('Error fetching pattern insights:', error);
    }
  };

  const handleApproval = async (fileId: string, action: 'approve' | 'reject', reason?: string) => {
    try {
      const response = await fetch('/api/admin/approve-file', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          fileId,
          action,
          reason: reason || ''
        })
      });

      if (response.ok) {
        // Refresh the pending files list
        await fetchPendingFiles();
        console.log(`File ${fileId} ${action}d successfully`);
      }
    } catch (error) {
      console.error(`Error ${action}ing file:`, error);
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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (roleLoading) {
    return (
      <div className="max-w-7xl mx-auto p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="max-w-7xl mx-auto p-6">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
          <Shield className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-red-800 mb-2">Access Denied</h2>
          <p className="text-red-600">You need Admin privileges to access this panel.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto p-6">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Admin Panel</h1>
      
      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('approvals')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'approvals'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center">
              <Clock className="w-4 h-4 mr-2" />
              File Approvals ({pendingFiles.filter(f => f.status === 'pending_approval').length})
            </div>
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'audit'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center">
              <Eye className="w-4 h-4 mr-2" />
              Audit Logs
            </div>
          </button>
          <button
            onClick={() => setActiveTab('patterns')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'patterns'
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center">
              <TrendingUp className="w-4 h-4 mr-2" />
              Pattern Insights
            </div>
          </button>
        </nav>
      </div>

      {/* File Approvals Tab */}
      {activeTab === 'approvals' && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Pending File Approvals</h2>
          
          {pendingFiles.filter(f => f.status === 'pending_approval').length === 0 ? (
            <div className="text-center py-8">
              <Check className="w-12 h-12 text-green-500 mx-auto mb-4" />
              <p className="text-gray-500">No files pending approval</p>
            </div>
          ) : (
            <div className="space-y-4">
              {pendingFiles
                .filter(f => f.status === 'pending_approval')
                .map((file) => (
                  <div key={file.file_id} className="bg-white rounded-lg border border-gray-200 p-6">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center mb-2">
                          <FileText className="w-5 h-5 text-gray-400 mr-2" />
                          <h3 className="text-lg font-medium text-gray-900">{file.file_name}</h3>
                        </div>
                        
                        <div className="grid grid-cols-2 gap-4 text-sm text-gray-600 mb-4">
                          <div className="flex items-center">
                            <User className="w-4 h-4 mr-1" />
                            Uploaded by: {file.uploaded_by}
                          </div>
                          <div className="flex items-center">
                            <Calendar className="w-4 h-4 mr-1" />
                            {formatDate(file.uploaded_at)}
                          </div>
                          <div>
                            Type: {file.file_type}
                          </div>
                          <div>
                            Size: {formatFileSize(file.file_size)}
                          </div>
                        </div>

                        {file.flagged_reasons.length > 0 && (
                          <div className="mb-4">
                            <div className="flex items-center mb-2">
                              <AlertTriangle className="w-4 h-4 text-orange-500 mr-2" />
                              <span className="text-sm font-medium text-orange-800">Flagged for:</span>
                            </div>
                            <ul className="list-disc list-inside text-sm text-orange-700 space-y-1">
                              {file.flagged_reasons.map((reason, index) => (
                                <li key={index}>{reason}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>

                      <div className="flex space-x-3 ml-6">
                        <button
                          onClick={() => handleApproval(file.file_id, 'approve')}
                          className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                        >
                          <Check className="w-4 h-4 mr-1" />
                          Approve
                        </button>
                        <button
                          onClick={() => handleApproval(file.file_id, 'reject', 'Rejected by admin')}
                          className="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                        >
                          <X className="w-4 h-4 mr-1" />
                          Reject
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
            </div>
          )}
        </div>
      )}

      {/* Audit Logs Tab */}
      {activeTab === 'audit' && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Recent Activity</h2>
          
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200">
              {auditLogs.map((log) => (
                <li key={log.log_id} className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center">
                        <div className="flex-shrink-0">
                          <User className="w-5 h-5 text-gray-400" />
                        </div>
                        <div className="ml-3">
                          <p className="text-sm font-medium text-gray-900">
                            {log.user_id}
                          </p>
                          <p className="text-sm text-gray-500">
                            {log.action} - {log.resource}
                          </p>
                        </div>
                      </div>
                    </div>
                    <div className="text-sm text-gray-500">
                      {formatDate(log.timestamp)}
                    </div>
                  </div>
                  {log.details && (
                    <div className="mt-2 text-xs text-gray-600 bg-gray-50 p-2 rounded">
                      <pre className="whitespace-pre-wrap">{JSON.stringify(JSON.parse(log.details), null, 2)}</pre>
                    </div>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Pattern Insights Tab */}
      {activeTab === 'patterns' && (
        <div>
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Pattern Insights & Analytics</h2>
          
          {patternInsights ? (
            <div className="space-y-6">
              {/* Summary Stats */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-blue-50 p-4 rounded-lg">
                  <div className="flex items-center">
                    <TrendingUp className="w-8 h-8 text-blue-600 mr-3" />
                    <div>
                      <p className="text-lg font-semibold text-blue-900">{patternInsights.total_patterns}</p>
                      <p className="text-sm text-blue-600">Total Patterns</p>
                    </div>
                  </div>
                </div>
                <div className="bg-green-50 p-4 rounded-lg">
                  <div className="flex items-center">
                    <Check className="w-8 h-8 text-green-600 mr-3" />
                    <div>
                      <p className="text-lg font-semibold text-green-900">{patternInsights.average_confidence * 100}%</p>
                      <p className="text-sm text-green-600">Avg Confidence</p>
                    </div>
                  </div>
                </div>
                <div className="bg-purple-50 p-4 rounded-lg">
                  <div className="flex items-center">
                    <FileText className="w-8 h-8 text-purple-600 mr-3" />
                    <div>
                      <p className="text-lg font-semibold text-purple-900">{Object.keys(patternInsights.pattern_types).length}</p>
                      <p className="text-sm text-purple-600">Pattern Types</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Top Insights */}
              {patternInsights.top_insights.length > 0 && (
                <div className="bg-white p-6 rounded-lg border">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Top Insights</h3>
                  <div className="space-y-4">
                    {patternInsights.top_insights.map((insight, index) => (
                      <div key={index} className="border-l-4 border-blue-500 pl-4">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-900">{insight.description}</h4>
                            <p className="text-sm text-gray-600 mt-1">{insight.details}</p>
                            <span className="inline-block mt-2 px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded">
                              {insight.type}
                            </span>
                          </div>
                          <span className="ml-4 text-sm font-medium text-green-600">
                            {Math.round(insight.confidence * 100)}% confidence
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Recommendations */}
              {patternInsights.recommendations.length > 0 && (
                <div className="bg-amber-50 p-6 rounded-lg border border-amber-200">
                  <h3 className="text-lg font-medium text-amber-900 mb-4 flex items-center">
                    <AlertTriangle className="w-5 h-5 mr-2" />
                    Recommendations
                  </h3>
                  <ul className="space-y-2">
                    {patternInsights.recommendations.map((recommendation, index) => (
                      <li key={index} className="flex items-start">
                        <span className="text-amber-600 mr-2">•</span>
                        <span className="text-amber-800">{recommendation}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Pattern Types Breakdown */}
              {Object.keys(patternInsights.pattern_types).length > 0 && (
                <div className="bg-white p-6 rounded-lg border">
                  <h3 className="text-lg font-medium text-gray-900 mb-4">Pattern Types Breakdown</h3>
                  <div className="space-y-2">
                    {Object.entries(patternInsights.pattern_types).map(([type, count]) => (
                      <div key={type} className="flex justify-between items-center">
                        <span className="text-gray-700 capitalize">{type.replace('_', ' ')}</span>
                        <span className="font-medium text-gray-900">{count}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="text-center py-8">
              <TrendingUp className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-500">No pattern insights available yet.</p>
              <p className="text-sm text-gray-400 mt-2">Patterns will appear as users interact with the system.</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}