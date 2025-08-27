'use client';

import { useState } from 'react';
import FileUpload from '@/components/upload/FileUpload';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { AlertCircle, CheckCircle, Clock, FileText } from 'lucide-react';

interface DocumentStatus {
  id: string;
  filename: string;
  status: 'uploading' | 'processing' | 'completed' | 'failed' | 'duplicate';
  progress?: number;
  error?: string;
  summary?: string;
  message?: string;
  existing_document?: {
    id: string;
    title: string;
    created_at: string;
  };
}

export default function UploadPage() {
  const [documents, setDocuments] = useState<DocumentStatus[]>([]);
  const [isUploading, setIsUploading] = useState(false);

  const handleUpload = async (files: File[]) => {
    setIsUploading(true);
    
    // Create FormData for file upload
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    // Add temporary documents to state
    const tempDocs: DocumentStatus[] = files.map((file) => ({
      id: Math.random().toString(36).substr(2, 9),
      filename: file.name,
      status: 'uploading',
      progress: 0
    }));
    
    setDocuments(prev => [...prev, ...tempDocs]);

    try {

      // Mock upload for now - replace with actual API call
      const response = await fetch('/api/documents/upload/', {
        method: 'POST',
        headers: {
          'Authorization': 'Bearer dev_token' // Mock token for development
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const result = await response.json();
      
      // Update documents with server response
      setDocuments(prev => prev.map(doc => {
        const serverDoc = result.uploaded_documents.find((d: any) => d.filename === doc.filename);
        if (serverDoc) {
          return {
            ...doc,
            id: serverDoc.id,
            status: serverDoc.status === 'duplicate' ? 'duplicate' : 'processing',
            message: serverDoc.message,
            existing_document: serverDoc.existing_document
          };
        }
        return doc;
      }));

      // Start polling for processing status (skip duplicates)
      result.uploaded_documents.forEach((doc: any) => {
        if (doc.status !== 'duplicate') {
          pollDocumentStatus(doc.id);
        }
      });

    } catch (error) {
      console.error('Upload error:', error);
      
      // Mark all temp documents as failed
      setDocuments(prev => prev.map(doc => 
        tempDocs.some(temp => temp.filename === doc.filename) 
          ? { ...doc, status: 'failed', error: 'Upload failed' }
          : doc
      ));
    } finally {
      setIsUploading(false);
    }
  };

  const pollDocumentStatus = async (documentId: string) => {
    const maxPolls = 30; // 1 minute max
    let polls = 0;
    
    const poll = async () => {
      try {
        const response = await fetch(`/api/documents/${documentId}/`, {
          headers: {
            'Authorization': 'Bearer dev_token'
          }
        });
        
        if (!response.ok) return;
        
        const doc = await response.json();
        
        setDocuments(prev => prev.map(d => 
          d.id === documentId 
            ? { 
                ...d, 
                status: doc.processing_status === 'completed' ? 'completed' : 
                       doc.processing_status === 'failed' ? 'failed' : 'processing',
                summary: doc.summary,
                error: doc.error_message
              }
            : d
        ));
        
        // Continue polling if still processing
        if (doc.processing_status === 'processing' && polls < maxPolls) {
          polls++;
          setTimeout(poll, 2000);
        }
        
      } catch (error) {
        console.error('Status polling error:', error);
      }
    };
    
    poll();
  };

  const getStatusIcon = (status: DocumentStatus['status']) => {
    switch (status) {
      case 'uploading':
        return <Clock className="h-5 w-5 text-blue-500 animate-pulse" />;
      case 'processing':
        return <div className="h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'failed':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'duplicate':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      default:
        return <FileText className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusText = (status: DocumentStatus['status']) => {
    switch (status) {
      case 'uploading': return 'Uploading...';
      case 'processing': return 'Processing document...';
      case 'completed': return 'Completed';
      case 'failed': return 'Failed';
      case 'duplicate': return 'Duplicate detected';
      default: return 'Unknown';
    }
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Document Upload
        </h1>
        <p className="text-gray-600">
          Upload your travel documents for AI-powered organization and analysis.
        </p>
      </div>

      {/* Upload Component */}
      <div className="mb-8">
        <FileUpload 
          onUpload={handleUpload}
          maxSize={4.5 * 1024 * 1024} // 4.5MB
          accept={{ 'application/pdf': ['.pdf'] }}
        />
      </div>

      {/* Document Status List */}
      {documents.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <FileText className="h-5 w-5" />
              <span>Upload Status ({documents.length})</span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-start justify-between p-4 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-start space-x-3 flex-1">
                    {getStatusIcon(doc.status)}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {doc.filename}
                      </p>
                      <p className="text-xs text-gray-500 mb-2">
                        {getStatusText(doc.status)}
                      </p>
                      
                      {doc.error && (
                        <p className="text-xs text-red-600 mb-2">
                          Error: {doc.error}
                        </p>
                      )}
                      
                      {doc.message && doc.status === 'duplicate' && (
                        <p className="text-xs text-yellow-600 mb-2">
                          {doc.message}
                        </p>
                      )}
                      
                      {doc.summary && (
                        <div className="text-xs text-gray-700 bg-white p-3 rounded border space-y-2">
                          <p><strong>Summary:</strong> {doc.summary}</p>
                          {/* Add structured data display */}
                          <div className="grid grid-cols-2 gap-2 pt-2 border-t">
                            <div><strong>Status:</strong> Processing completed</div>
                            <div><strong>Category:</strong> Transport Document</div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  {doc.status === 'completed' && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        // Navigate to document view - implement later
                        console.log('View document:', doc.id);
                      }}
                    >
                      View
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Development Info */}
      <Card className="mt-8 bg-blue-50 border-blue-200">
        <CardContent className="pt-6">
          <h3 className="text-sm font-medium text-blue-900 mb-2">
            🚧 Development Mode
          </h3>
          <p className="text-xs text-blue-800">
            This is Phase 2 implementation. Features included:
          </p>
          <ul className="text-xs text-blue-800 mt-2 space-y-1 list-disc list-inside">
            <li>Drag & drop file upload (PDF only, 4.5MB max)</li>
            <li>File validation and error handling</li>
            <li>Background document processing with Docling</li>
            <li>AI-powered classification and extraction with Claude</li>
            <li>Real-time status updates</li>
          </ul>
          <p className="text-xs text-blue-600 mt-3">
            <strong>Note:</strong> Set ANTHROPIC_API_KEY in your environment for AI features.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}