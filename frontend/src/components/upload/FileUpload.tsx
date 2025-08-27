'use client';

import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, AlertCircle, CheckCircle, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';

interface FileUploadProps {
  onUpload?: (files: File[]) => void;
  maxSize?: number;
  accept?: Record<string, string[]>;
}

interface UploadedFile {
  file: File;
  id: string;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'error';
  progress?: number;
  error?: string;
}

export default function FileUpload({ 
  onUpload, 
  maxSize = 4.5 * 1024 * 1024, // 4.5MB default
  accept = { 'application/pdf': ['.pdf'] }
}: FileUploadProps) {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const onDrop = useCallback((acceptedFiles: File[], rejectedFiles: any) => {
    // Handle rejected files
    if (rejectedFiles.length > 0) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      rejectedFiles.forEach((rejection: any) => {
        const error = rejection.errors[0]?.message || 'File rejected';
        console.error(`File ${rejection.file.name} rejected: ${error}`);
      });
    }

    // Handle accepted files
    if (acceptedFiles.length > 0) {
      const newFiles: UploadedFile[] = acceptedFiles.map((file) => ({
        file,
        id: Math.random().toString(36).substr(2, 9),
        status: 'pending'
      }));

      setUploadedFiles(prev => [...prev, ...newFiles]);
      onUpload?.(acceptedFiles);
    }
  }, [onUpload]);

  const { getRootProps, getInputProps, isDragActive, isDragAccept, isDragReject } = useDropzone({
    onDrop,
    accept,
    maxSize,
    multiple: true
  });

  const removeFile = (id: string) => {
    setUploadedFiles(prev => prev.filter(f => f.id !== id));
  };

  const getDropzoneClassName = () => {
    let className = "border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ";
    
    if (isDragAccept) {
      className += "border-green-400 bg-green-50";
    } else if (isDragReject) {
      className += "border-red-400 bg-red-50";
    } else if (isDragActive) {
      className += "border-blue-400 bg-blue-50";
    } else {
      className += "border-gray-300 hover:border-gray-400";
    }
    
    return className;
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusIcon = (status: UploadedFile['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-5 w-5 text-red-500" />;
      case 'uploading':
      case 'processing':
        return (
          <div className="h-5 w-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        );
      default:
        return <File className="h-5 w-5 text-gray-500" />;
    }
  };

  const getStatusText = (status: UploadedFile['status']) => {
    switch (status) {
      case 'pending': return 'Ready to upload';
      case 'uploading': return 'Uploading...';
      case 'processing': return 'Processing document...';
      case 'completed': return 'Completed';
      case 'error': return 'Error occurred';
      default: return '';
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto space-y-6">
      {/* Drop zone */}
      <Card>
        <CardContent className="p-6">
          <div {...getRootProps()} className={getDropzoneClassName()}>
            <input {...getInputProps()} />
            <Upload className="h-12 w-12 mx-auto mb-4 text-gray-400" />
            
            {isDragActive ? (
              <p className="text-lg font-medium text-blue-600">
                Drop the files here...
              </p>
            ) : (
              <div>
                <p className="text-lg font-medium text-gray-900 mb-2">
                  Drag & drop PDF files here, or click to select
                </p>
                <p className="text-sm text-gray-500">
                  Maximum file size: {formatFileSize(maxSize)} • PDF files only
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* File list */}
      {uploadedFiles.length > 0 && (
        <Card>
          <CardContent className="p-6">
            <h3 className="text-lg font-semibold mb-4">
              Uploaded Files ({uploadedFiles.length})
            </h3>
            
            <div className="space-y-3">
              {uploadedFiles.map((uploadedFile) => (
                <div
                  key={uploadedFile.id}
                  className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                >
                  <div className="flex items-center space-x-3 flex-1">
                    {getStatusIcon(uploadedFile.status)}
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {uploadedFile.file.name}
                      </p>
                      <div className="flex items-center space-x-2 text-xs text-gray-500">
                        <span>{formatFileSize(uploadedFile.file.size)}</span>
                        <span>•</span>
                        <span>{getStatusText(uploadedFile.status)}</span>
                      </div>
                      {uploadedFile.error && (
                        <p className="text-xs text-red-600 mt-1">
                          {uploadedFile.error}
                        </p>
                      )}
                    </div>
                  </div>
                  
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFile(uploadedFile.id)}
                    className="text-gray-400 hover:text-red-500"
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}