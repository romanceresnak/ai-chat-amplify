'use client';

import { useDropzone } from 'react-dropzone';
import { useState } from 'react';

export default function TestDropzonePage() {
  const [files, setFiles] = useState<File[]>([]);
  const [logs, setLogs] = useState<string[]>([]);

  const addLog = (message: string) => {
    setLogs(prev => [...prev, `${new Date().toISOString()}: ${message}`]);
    console.log(message);
  };

  const onDrop = (acceptedFiles: File[]) => {
    addLog(`Files dropped: ${acceptedFiles.length}`);
    acceptedFiles.forEach(file => {
      addLog(`File: ${file.name} (${file.size} bytes)`);
    });
    setFiles(acceptedFiles);
  };

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDragEnter: () => addLog('Drag enter'),
    onDragLeave: () => addLog('Drag leave'),
    onDragOver: () => addLog('Drag over'),
    onError: (err) => addLog(`Error: ${err}`),
  });

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold mb-4">Drag and Drop Test</h1>
      
      <div
        {...getRootProps()}
        className={`
          w-full h-64 border-4 border-dashed rounded-lg
          flex flex-col items-center justify-center cursor-pointer
          transition-all duration-200
          ${isDragActive 
            ? 'border-blue-500 bg-blue-50 scale-105' 
            : 'border-gray-300 bg-gray-50 hover:border-gray-400'
          }
        `}
      >
        <input {...getInputProps()} />
        <p className="text-lg font-semibold mb-2">
          {isDragActive ? '📥 Drop files here' : '📤 Drag files here'}
        </p>
        <p className="text-gray-600">or click to select files</p>
      </div>

      {files.length > 0 && (
        <div className="mt-4">
          <h2 className="font-semibold mb-2">Dropped Files:</h2>
          <ul className="list-disc pl-6">
            {files.map((file, index) => (
              <li key={index}>{file.name} - {file.size} bytes</li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4">
        <h2 className="font-semibold mb-2">Event Logs:</h2>
        <div className="bg-black text-green-400 p-4 rounded font-mono text-sm max-h-64 overflow-auto">
          {logs.map((log, index) => (
            <div key={index}>{log}</div>
          ))}
        </div>
      </div>

      <div className="mt-4 text-sm text-gray-600">
        <p>React version: {require('react').version}</p>
        <p>react-dropzone version: {require('react-dropzone').version || 'unknown'}</p>
      </div>
    </div>
  );
}