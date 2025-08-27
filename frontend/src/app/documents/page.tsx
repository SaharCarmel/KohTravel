'use client';

import { useState, useEffect } from 'react';
import { useSession } from 'next-auth/react';
import Link from 'next/link';
import { Search, Filter, SortAsc, Plus, FileText, Calendar, Tag, Trash2, Eye, Upload, ChevronDown, ChevronUp, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useDropzone } from 'react-dropzone';
import { useCallback } from 'react';

interface Document {
  id: string;
  title: string;
  original_filename: string;
  category_id: number;
  processing_status: string;
  confidence_score: number;
  created_at: string;
  updated_at: string;
  summary: string;
  error_message?: string;
}

interface Category {
  id: number;
  name: string;
  keywords: string[];
  extraction_fields: Record<string, string>;
}

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

export default function DocumentsPage() {
  const { data: session } = useSession();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [filteredDocuments, setFilteredDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedStatus, setSelectedStatus] = useState<string>('all');
  const [sortBy, setSortBy] = useState<string>('date_desc');
  
  // Upload state
  const [uploadDocuments, setUploadDocuments] = useState<DocumentStatus[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [showProcessing, setShowProcessing] = useState(true);

  useEffect(() => {
    fetchDocuments();
    fetchCategories();
  }, []);

  useEffect(() => {
    filterAndSortDocuments();
  }, [documents, searchQuery, selectedCategory, selectedStatus, sortBy]);

  const getAuthHeaders = () => {
    try {
      // Get the NextAuth session token from cookies
      const getCookie = (name: string) => {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop()?.split(';').shift();
        return null;
      };

      // Try different cookie names that NextAuth might use
      const cookieNames = [
        'next-auth.session-token',
        '__Secure-next-auth.session-token',
        'nextauth.session-token'
      ];
      
      let sessionToken = null;
      for (const cookieName of cookieNames) {
        sessionToken = getCookie(cookieName);
        if (sessionToken) {
          console.log(`Found NextAuth token in cookie: ${cookieName}`);
          break;
        }
      }
      
      if (sessionToken) {
        return {
          'Authorization': `Bearer ${sessionToken}`,
          'Content-Type': 'application/json'
        };
      } else {
        console.log('No NextAuth session token found, using dev_token fallback');
        return {
          'Authorization': 'Bearer dev_token',
          'Content-Type': 'application/json'
        };
      }
    } catch (error) {
      console.error('Error getting auth headers:', error);
      return {
        'Authorization': 'Bearer dev_token',
        'Content-Type': 'application/json'
      };
    }
  };

  const fetchDocuments = async () => {
    try {
      const response = await fetch('/api/documents/', {
        headers: getAuthHeaders()
      });
      
      if (response.ok) {
        const data = await response.json();
        setDocuments(data.documents);
      }
    } catch (error) {
      console.error('Error fetching documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch('/api/documents/categories/', {
        headers: getAuthHeaders()
      });
      if (response.ok) {
        const data = await response.json();
        setCategories(data.categories);
      }
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const filterAndSortDocuments = () => {
    let filtered = documents.filter(doc => {
      // Search filter
      const matchesSearch = searchQuery === '' || 
        doc.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        doc.summary?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        doc.original_filename.toLowerCase().includes(searchQuery.toLowerCase());

      // Category filter
      const matchesCategory = selectedCategory === 'all' || 
        doc.category_id?.toString() === selectedCategory;

      // Status filter
      const matchesStatus = selectedStatus === 'all' || 
        doc.processing_status === selectedStatus;

      return matchesSearch && matchesCategory && matchesStatus;
    });

    // Sort documents
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'date_desc':
          return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
        case 'date_asc':
          return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        case 'name_asc':
          return a.title.localeCompare(b.title);
        case 'name_desc':
          return b.title.localeCompare(a.title);
        case 'status':
          return a.processing_status.localeCompare(b.processing_status);
        default:
          return 0;
      }
    });

    setFilteredDocuments(filtered);
  };

  const getCategoryName = (categoryId: number) => {
    const category = categories.find(cat => cat.id === categoryId);
    return category?.name || 'Uncategorized';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'text-green-600 bg-green-50';
      case 'processing': return 'text-blue-600 bg-blue-50';
      case 'failed': return 'text-red-600 bg-red-50';
      case 'pending': return 'text-yellow-600 bg-yellow-50';
      default: return 'text-gray-600 bg-gray-50';
    }
  };

  const handleDelete = async (documentId: string) => {
    if (!confirm('Are you sure you want to delete this document?')) {
      return;
    }

    try {
      const response = await fetch(`/api/documents/${documentId}/`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });

      if (response.ok) {
        setDocuments(prev => prev.filter(doc => doc.id !== documentId));
      } else {
        alert('Failed to delete document');
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      alert('Error deleting document');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const handleUpload = async (files: File[]) => {
    setIsUploading(true);
    
    const formData = new FormData();
    files.forEach((file) => {
      formData.append('files', file);
    });

    try {
      const tempDocs: DocumentStatus[] = files.map((file) => ({
        id: Math.random().toString(36).substr(2, 9),
        filename: file.name,
        status: 'uploading',
        progress: 0
      }));
      
      setUploadDocuments(prev => [...prev, ...tempDocs]);

      const authHeaders = getAuthHeaders();
      const response = await fetch('/api/documents/upload/', {
        method: 'POST',
        headers: {
          'Authorization': authHeaders['Authorization']
        },
        body: formData
      });

      if (!response.ok) {
        throw new Error('Upload failed');
      }

      const result = await response.json();
      
      setUploadDocuments(prev => prev.map(doc => {
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

      result.uploaded_documents.forEach((doc: any) => {
        if (doc.status !== 'duplicate') {
          pollDocumentStatus(doc.id);
        }
      });

    } catch (error) {
      console.error('Upload error:', error);
      
      setUploadDocuments(prev => prev.map(doc => 
        files.some(file => file.name === doc.filename) 
          ? { ...doc, status: 'failed', error: 'Upload failed' }
          : doc
      ));
    } finally {
      setIsUploading(false);
    }
  };

  const pollDocumentStatus = async (documentId: string) => {
    const maxPolls = 30;
    let polls = 0;
    
    const poll = async () => {
      try {
        const response = await fetch(`/api/documents/${documentId}/`, {
          headers: getAuthHeaders()
        });
        
        if (!response.ok) return;
        
        const doc = await response.json();
        
        setUploadDocuments(prev => prev.map(upload => 
          upload.id === documentId 
            ? {
                ...upload,
                status: doc.processing_status === 'completed' ? 'completed' : 
                       doc.processing_status === 'failed' ? 'failed' : 'processing',
                summary: doc.summary,
                error: doc.error_message
              }
            : upload
        ));

        if (doc.processing_status === 'completed' || doc.processing_status === 'failed') {
          // Refresh the main documents list
          fetchDocuments();
          return;
        }

        polls++;
        if (polls < maxPolls) {
          setTimeout(poll, 2000);
        }
      } catch (error) {
        console.error('Error polling document status:', error);
      }
    };

    poll();
  };

  // Dropzone setup
  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      handleUpload(acceptedFiles);
    }
  }, [handleUpload]);

  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
    multiple: true
  });

  const getDropzoneClassName = () => {
    let className = "cursor-pointer transition-colors duration-200 ";
    
    if (isDragAccept) {
      className += "border-green-400 bg-green-50";
    } else if (isDragReject) {
      className += "border-red-400 bg-red-50";
    } else if (isDragActive) {
      className += "border-blue-400 bg-blue-50";
    } else {
      className += "hover:border-blue-400 hover:bg-gray-50";
    }
    
    return className;
  };

  const getUploadStatusIcon = (status: string) => {
    switch (status) {
      case 'uploading': return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'processing': return <Clock className="h-4 w-4 text-blue-500 animate-pulse" />;
      case 'completed': return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'failed': return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'duplicate': return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      default: return <FileText className="h-4 w-4 text-gray-400" />;
    }
  };

  if (loading) {
    return (
      <div className="container mx-auto py-8 px-4">
        <div className="flex items-center justify-center min-h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Documents</h1>
        <p className="text-gray-600">
          Upload, organize and manage your travel documents with AI-powered analysis
        </p>
      </div>

      {/* Always Visible Upload Zone */}
      <Card className={`upload-zone mb-6 border-2 border-dashed border-gray-300 ${getDropzoneClassName()}`}>
        <CardContent className="p-8">
          <div {...getRootProps()} className="text-center">
            <input {...getInputProps()} disabled={isUploading} />
            <Upload className={`h-16 w-16 mx-auto mb-4 transition-colors ${
              isDragActive ? 'text-blue-500' : 'text-gray-400'
            }`} />
            
            {isDragActive ? (
              <div>
                <p className="text-xl font-medium text-blue-600 mb-2">
                  {isDragAccept ? 'Drop files here...' : 'Some files not supported'}
                </p>
                <p className="text-sm text-gray-500">
                  Release to upload
                </p>
              </div>
            ) : (
              <div>
                <p className="text-xl font-medium text-gray-900 mb-2">
                  Drag & drop files here, or click to select
                </p>
                <p className="text-sm text-gray-500 mb-2">
                  Supports: <span className="font-medium">PDF, DOC, DOCX, JPG, PNG</span> • Max: <span className="font-medium">10MB per file</span>
                </p>
                <p className="text-xs text-gray-400">
                  AI will automatically categorize and extract key information from your documents
                </p>
              </div>
            )}
            
            {isUploading && (
              <div className="mt-4">
                <div className="inline-flex items-center px-4 py-2 bg-blue-50 text-blue-700 rounded-lg">
                  <Clock className="h-4 w-4 mr-2 animate-spin" />
                  Uploading files...
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Processing Section - Collapsible */}
      {uploadDocuments.length > 0 && (
        <Card className="mb-6">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="flex items-center text-lg">
                <Clock className="h-5 w-5 mr-2 text-blue-500" />
                Processing Documents ({uploadDocuments.filter(d => d.status === 'processing' || d.status === 'uploading').length})
              </CardTitle>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setShowProcessing(!showProcessing)}
              >
                {showProcessing ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </Button>
            </div>
          </CardHeader>
          {showProcessing && (
            <CardContent className="pt-0">
              <div className="space-y-3">
                {uploadDocuments.map((doc) => (
                  <div key={doc.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border">
                    <div className="flex items-center space-x-3">
                      {getUploadStatusIcon(doc.status)}
                      <div>
                        <p className="text-sm font-medium text-gray-900">{doc.filename}</p>
                        {doc.message && (
                          <p className="text-xs text-gray-500">{doc.message}</p>
                        )}
                        {doc.error && (
                          <p className="text-xs text-red-500">{doc.error}</p>
                        )}
                        {doc.summary && (
                          <p className="text-xs text-gray-600 mt-1">{doc.summary}</p>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`text-xs font-medium px-3 py-1 rounded-full ${
                        doc.status === 'completed' ? 'text-green-700 bg-green-100' :
                        doc.status === 'failed' ? 'text-red-700 bg-red-100' :
                        doc.status === 'duplicate' ? 'text-yellow-700 bg-yellow-100' :
                        'text-blue-700 bg-blue-100'
                      }`}>
                        {doc.status === 'duplicate' ? 'Duplicate' : 
                         doc.status === 'uploading' ? 'Uploading...' :
                         doc.status === 'processing' ? 'Analyzing...' :
                         doc.status}
                      </span>
                      {doc.existing_document && (
                        <p className="text-xs text-gray-500 mt-1">
                          Similar to: {doc.existing_document.title}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          )}
        </Card>
      )}

      {/* Filters and Search */}
      <Card className="mb-6">
        <CardContent className="p-6">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-3 top-3 h-4 w-4 text-gray-400" />
              <Input
                placeholder="Search documents..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Category Filter */}
            <Select value={selectedCategory} onValueChange={setSelectedCategory}>
              <SelectTrigger>
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="All Categories" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Categories</SelectItem>
                {categories.map(category => (
                  <SelectItem key={category.id} value={category.id.toString()}>
                    {category.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Status Filter */}
            <Select value={selectedStatus} onValueChange={setSelectedStatus}>
              <SelectTrigger>
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="processing">Processing</SelectItem>
                <SelectItem value="failed">Failed</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
              </SelectContent>
            </Select>

            {/* Sort */}
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger>
                <SortAsc className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="date_desc">Newest First</SelectItem>
                <SelectItem value="date_asc">Oldest First</SelectItem>
                <SelectItem value="name_asc">Name A-Z</SelectItem>
                <SelectItem value="name_desc">Name Z-A</SelectItem>
                <SelectItem value="status">Status</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Documents Grid */}
      {filteredDocuments.length === 0 ? (
        <Card>
          <CardContent className="p-12 text-center">
            <FileText className="h-16 w-16 text-gray-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-600 mb-2">No documents found</h3>
            <p className="text-gray-500 mb-6">
              {documents.length === 0 
                ? "Upload your first travel document to get started"
                : "Try adjusting your search or filters"
              }
            </p>
            {documents.length === 0 && (
              <Button onClick={() => {
                // Scroll to upload section
                const uploadSection = document.querySelector('.upload-zone');
                uploadSection?.scrollIntoView({ behavior: 'smooth' });
              }}>
                <Upload className="h-4 w-4 mr-2" />
                Upload Your First Document
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredDocuments.map(document => (
            <Card key={document.id} className="hover:shadow-lg transition-shadow cursor-pointer">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <CardTitle className="text-lg font-medium text-gray-900 truncate">
                      {document.title}
                    </CardTitle>
                    <p className="text-sm text-gray-500 mt-1">
                      {document.original_filename}
                    </p>
                  </div>
                  <div className="flex space-x-1 ml-2">
                    <Link href={`/documents/${document.id}`}>
                      <Button variant="ghost" size="sm">
                        <Eye className="h-4 w-4" />
                      </Button>
                    </Link>
                    <Button 
                      variant="ghost" 
                      size="sm"
                      onClick={() => handleDelete(document.id)}
                      className="text-red-500 hover:text-red-700 hover:bg-red-50"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {/* Category and Status */}
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <Tag className="h-4 w-4 text-gray-400 mr-2" />
                      <span className="text-sm text-gray-600">
                        {getCategoryName(document.category_id)}
                      </span>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(document.processing_status)}`}>
                      {document.processing_status}
                    </span>
                  </div>

                  {/* Summary */}
                  {document.summary && (
                    <p className="text-sm text-gray-600 line-clamp-2">
                      {document.summary}
                    </p>
                  )}

                  {/* Date and Confidence */}
                  <div className="flex items-center justify-between text-xs text-gray-500">
                    <div className="flex items-center">
                      <Calendar className="h-3 w-3 mr-1" />
                      {formatDate(document.created_at)}
                    </div>
                    {document.confidence_score && (
                      <span>
                        {Math.round(document.confidence_score * 100)}% confidence
                      </span>
                    )}
                  </div>

                  {/* Error message */}
                  {document.error_message && (
                    <p className="text-xs text-red-500 bg-red-50 p-2 rounded">
                      Error: {document.error_message}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Summary Stats */}
      {documents.length > 0 && (
        <div className="mt-8 text-center text-sm text-gray-500">
          Showing {filteredDocuments.length} of {documents.length} documents
        </div>
      )}
    </div>
  );
}