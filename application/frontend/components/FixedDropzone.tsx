'use client';

import React, { useCallback, useState } from 'react';
import { Upload } from 'lucide-react';

interface FixedDropzoneProps {
  onDrop: (files: File[]) => void;
  disabled?: boolean;
  className?: string;
  children?: React.ReactNode;
}

export function FixedDropzone({ onDrop, disabled, className, children }: FixedDropzoneProps) {
  const [isDragActive, setIsDragActive] = useState(false);
  
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Drag enter event');
    setIsDragActive(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Drag leave event');
    
    // Check if we're actually leaving the drop zone
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    if (
      e.clientX <= rect.left ||
      e.clientX >= rect.right ||
      e.clientY <= rect.top ||
      e.clientY >= rect.bottom
    ) {
      setIsDragActive(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Drag over event');
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('Drop event');
    setIsDragActive(false);

    if (disabled) return;

    const files = Array.from(e.dataTransfer.files);
    console.log(`Dropped ${files.length} files`);
    
    if (files.length > 0) {
      onDrop(files);
    }
  }, [disabled, onDrop]);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (disabled) return;
    
    const files = Array.from(e.target.files || []);
    if (files.length > 0) {
      onDrop(files);
    }
  }, [disabled, onDrop]);

  return (
    <div
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      className={className}
      style={{ position: 'relative' }}
    >
      <input
        type="file"
        multiple
        onChange={handleFileInput}
        style={{
          position: 'absolute',
          left: 0,
          top: 0,
          right: 0,
          bottom: 0,
          opacity: 0,
          cursor: disabled ? 'not-allowed' : 'pointer',
        }}
        disabled={disabled}
      />
      {children || (
        <div className="flex items-center gap-2">
          <Upload className="w-5 h-5 text-gray-500" />
          <span className="text-sm text-gray-600">
            {isDragActive ? "Drop here" : "Upload"}
          </span>
        </div>
      )}
    </div>
  );
}