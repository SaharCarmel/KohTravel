'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { 
  ArrowLeft, 
  Calendar, 
  Tag, 
  FileText, 
  MapPin, 
  DollarSign, 
  Hash, 
  User, 
  Clock,
  Edit,
  Trash2,
  RefreshCw,
  Download
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

interface Document {
  id: string;
  title: string;
  original_filename: string;
  category_id: number;
  raw_text: string;
  summary: string;
  structured_data: Record<string, any>;
  processing_status: string;
  confidence_score: number;
  error_message?: string;
  created_at: string;
  updated_at: string;
  quick_refs: Array<{
    field_name: string;
    field_value: string;
    field_type: string;
  }>;
}

interface Category {
  id: number;
  name: string;
}

export default function DocumentViewerPage() {
  const params = useParams();
  const router = useRouter();
  const documentId = params.id as string;

  const [document, setDocument] = useState<Document | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<'overview' | 'raw_text' | 'structured'>('overview');

  useEffect(() => {
    if (documentId) {
      fetchDocument();
      fetchCategories();
    }
  }, [documentId]);

  const fetchDocument = async () => {
    try {
      const response = await fetch(`/api/documents/${documentId}/`, {
        headers: {
          'Authorization': 'Bearer dev_token'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        setDocument(data);
      } else if (response.status === 404) {
        router.push('/documents');
      }
    } catch (error) {
      console.error('Error fetching document:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch('/api/documents/categories/');
      if (response.ok) {
        const data = await response.json();
        setCategories(data.categories);
      }
    } catch (error) {
      console.error('Error fetching categories:', error);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this document? This action cannot be undone.')) {
      return;
    }

    try {
      const response = await fetch(`/api/documents/${documentId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': 'Bearer dev_token'
        }
      });

      if (response.ok) {
        router.push('/documents');
      } else {
        alert('Failed to delete document');
      }
    } catch (error) {
      console.error('Error deleting document:', error);
      alert('Error deleting document');
    }
  };

  const getCategoryName = (categoryId: number) => {
    const category = categories.find(cat => cat.id === categoryId);
    return category?.name || 'Uncategorized';
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return 'bg-green-100 text-green-800 border-green-200';
      case 'processing': return 'bg-blue-100 text-blue-800 border-blue-200';
      case 'failed': return 'bg-red-100 text-red-800 border-red-200';
      case 'pending': return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      default: return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const renderQuickRefIcon = (type: string) => {
    switch (type) {
      case 'currency': return <DollarSign className="h-4 w-4" />;
      case 'date': return <Calendar className="h-4 w-4" />;
      case 'location': return <MapPin className="h-4 w-4" />;
      default: return <Hash className="h-4 w-4" />;
    }
  };

  const renderStructuredData = (data: Record<string, any>) => {
    const entries = Object.entries(data);
    
    return (
      <div className="space-y-4">
        {entries.map(([key, value]) => (
          <div key={key} className="border rounded-lg p-4">
            <h4 className="font-semibold text-gray-900 mb-2 capitalize">
              {key.replace(/_/g, ' ')}
            </h4>
            <div className="space-y-2">
              {typeof value === 'object' && value !== null ? (
                Array.isArray(value) ? (
                  <ul className="list-disc list-inside space-y-1">
                    {value.map((item, index) => (
                      <li key={index} className="text-sm text-gray-600">
                        {typeof item === 'object' ? JSON.stringify(item, null, 2) : String(item)}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {Object.entries(value).map(([subKey, subValue]) => (
                      <div key={subKey} className="flex justify-between">
                        <span className="text-sm font-medium text-gray-700 capitalize">
                          {subKey.replace(/_/g, ' ')}:
                        </span>
                        <span className="text-sm text-gray-600">
                          {String(subValue)}
                        </span>
                      </div>
                    ))}
                  </div>
                )
              ) : (
                <p className="text-sm text-gray-600">{String(value)}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    );
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
      </div>
    );
  }

  if (!document) {
    return (
      <div className="h-full flex items-center justify-center p-6">
        <Card>
          <CardContent className="p-8 text-center">
            <FileText className="h-12 w-12 text-gray-300 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-600 mb-2">Document not found</h3>
            <p className="text-sm text-gray-500 mb-4">The document you're looking for doesn't exist.</p>
            <Link href="/documents">
              <Button>Back to Documents</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-slate-50">
      <div className="flex-shrink-0 px-6 py-3 bg-white border-b">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link href="/documents">
              <Button variant="ghost" size="sm">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back to Documents
              </Button>
            </Link>
          </div>
          
          <div className="flex items-center space-x-2">
            <Button variant="outline" size="sm">
              <Edit className="h-4 w-4 mr-2" />
              Edit
            </Button>
            <Button variant="outline" size="sm">
              <RefreshCw className="h-4 w-4 mr-2" />
              Reprocess
            </Button>
            <Button 
              variant="outline" 
              size="sm" 
              onClick={handleDelete}
              className="text-red-600 hover:text-red-700 hover:bg-red-50"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </Button>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0 scrollable-content px-6 py-4">

        {/* Document Header */}
        <Card className="mb-4">
          <CardHeader className="pb-3">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between">
              <div className="flex-1">
                <CardTitle className="text-xl font-bold text-gray-900 mb-2">
                  {document.title}
                </CardTitle>
                <p className="text-sm text-gray-600 mb-3">
                  {document.original_filename}
                </p>
                
                <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500">
                  <div className="flex items-center">
                    <Tag className="h-3 w-3 mr-1" />
                    {getCategoryName(document.category_id)}
                  </div>
                  <div className="flex items-center">
                    <Calendar className="h-3 w-3 mr-1" />
                    {formatDate(document.created_at)}
                  </div>
                  <div className="flex items-center">
                    <Clock className="h-3 w-3 mr-1" />
                    Updated {formatDate(document.updated_at)}
                  </div>
                </div>
              </div>
              
              <div className="flex flex-col items-end space-y-2 mt-3 md:mt-0">
                <Badge className={getStatusColor(document.processing_status)}>
                  {document.processing_status}
                </Badge>
                {document.confidence_score && (
                  <span className="text-xs text-gray-500">
                    {Math.round(document.confidence_score * 100)}% confidence
                  </span>
                )}
              </div>
            </div>
          </CardHeader>
        </Card>

        {/* Quick References */}
        {document.quick_refs && document.quick_refs.length > 0 && (
          <Card className="mb-4">
            <CardHeader className="pb-3">
              <CardTitle className="text-base">Quick References</CardTitle>
            </CardHeader>
            <CardContent className="pt-0">
              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
                {document.quick_refs.map((ref, index) => (
                  <div key={index} className="flex items-center p-3 bg-gray-50 rounded border">
                    {renderQuickRefIcon(ref.field_type)}
                    <div className="ml-2">
                      <p className="text-xs text-gray-500 uppercase tracking-wide">
                        {ref.field_name.replace(/_/g, ' ')}
                      </p>
                      <p className="text-sm font-medium text-gray-900">
                        {ref.field_value || 'Not available'}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Content Tabs */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex space-x-1">
              {[
                { id: 'overview', label: 'Overview' },
                { id: 'structured', label: 'Structured Data' },
                { id: 'raw_text', label: 'Raw Text' }
              ].map(tab => (
                <Button
                  key={tab.id}
                  variant={activeTab === tab.id ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setActiveTab(tab.id as typeof activeTab)}
                >
                  {tab.label}
                </Button>
              ))}
            </div>
          </CardHeader>
          
          <CardContent className="pt-0">
            {activeTab === 'overview' && (
              <div className="space-y-4">
                {/* Summary */}
                {document.summary && (
                  <div>
                    <h3 className="text-base font-semibold text-gray-900 mb-2">Summary</h3>
                    <p className="text-sm text-gray-700 leading-relaxed bg-blue-50 p-3 rounded">
                      {document.summary}
                    </p>
                  </div>
                )}

                {/* Error Message */}
                {document.error_message && (
                  <div>
                    <h3 className="text-base font-semibold text-red-900 mb-2">Processing Error</h3>
                    <p className="text-sm text-red-700 bg-red-50 p-3 rounded">
                      {document.error_message}
                    </p>
                  </div>
                )}

                {/* Key Information */}
                {document.structured_data && Object.keys(document.structured_data).length > 0 && (
                  <div>
                    <h3 className="text-base font-semibold text-gray-900 mb-2">Key Information</h3>
                    {renderStructuredData(document.structured_data)}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'structured' && (
              <div>
                <h3 className="text-base font-semibold text-gray-900 mb-3">Structured Data</h3>
                {document.structured_data && Object.keys(document.structured_data).length > 0 ? (
                  <pre className="bg-gray-50 p-3 rounded overflow-x-auto text-xs">
                    {JSON.stringify(document.structured_data, null, 2)}
                  </pre>
                ) : (
                  <p className="text-sm text-gray-500 italic">No structured data available</p>
                )}
              </div>
            )}

            {activeTab === 'raw_text' && (
              <div>
                <h3 className="text-base font-semibold text-gray-900 mb-3">Raw Extracted Text</h3>
                {document.raw_text ? (
                  <div className="bg-gray-50 p-3 rounded max-h-80 overflow-y-auto">
                    <pre className="whitespace-pre-wrap text-xs text-gray-700">
                      {document.raw_text}
                    </pre>
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 italic">No raw text available</p>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}