import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { uploadDocument } from '../api';

export default function UploadZone({ onDocumentUploaded }) {
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState('idle'); // idle | uploading | success | error
  const [message, setMessage] = useState('');
  const inputRef = useRef(null);

  const handleFiles = async (fileList) => {
    const files = Array.from(fileList).filter(f => f.name.toLowerCase().endsWith('.pdf'));
    if (files.length === 0) {
      setStatus('error');
      setMessage('Only PDF files are supported.');
      setTimeout(() => setStatus('idle'), 3000);
      return;
    }

    setStatus('uploading');
    setMessage('');

    try {
      const result = await uploadDocument(files);
      setStatus('success');
      const docs = result.documents || [result];
      setMessage(`${docs.length} file${docs.length !== 1 ? 's' : ''} uploaded`);
      docs.forEach(doc => onDocumentUploaded(doc));
      setTimeout(() => setStatus('idle'), 3000);
    } catch (err) {
      setStatus('error');
      setMessage(err.message);
      setTimeout(() => setStatus('idle'), 4000);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const onInputChange = (e) => {
    handleFiles(e.target.files);
    e.target.value = '';
  };

  const borderColor = isDragging
    ? 'border-teal-500 bg-teal-50'
    : status === 'error'
    ? 'border-red-400 bg-red-50'
    : status === 'success'
    ? 'border-teal-400 bg-teal-50'
    : 'border-teal-200 bg-white/60 hover:border-teal-400 hover:bg-teal-50/60';

  return (
    <div className="space-y-2">
      <p className="text-xs font-semibold text-teal-700 uppercase tracking-wider">Upload PDF</p>
      <motion.div
        animate={isDragging ? { scale: 1.02 } : { scale: 1 }}
        transition={{ duration: 0.15 }}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => status !== 'uploading' && inputRef.current?.click()}
        className={`relative cursor-pointer rounded-xl border-2 border-dashed p-5 text-center transition-colors duration-200 ${borderColor}`}
        role="button"
        aria-label="Upload PDF file"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          multiple
          className="sr-only"
          onChange={onInputChange}
          aria-label="Select PDF files"
        />

        <AnimatePresence mode="wait">
          {status === 'uploading' && (
            <motion.div
              key="uploading"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-2"
            >
              <svg className="w-8 h-8 text-teal-500 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <p className="text-sm font-medium text-teal-700">Processing PDF…</p>
            </motion.div>
          )}

          {status === 'success' && (
            <motion.div
              key="success"
              initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-1"
            >
              <svg className="w-8 h-8 text-teal-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm font-medium text-teal-700">Uploaded!</p>
              <p className="text-xs text-teal-600 truncate max-w-full">{message}</p>
            </motion.div>
          )}

          {status === 'error' && (
            <motion.div
              key="error"
              initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-1"
            >
              <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm font-medium text-red-600">Upload failed</p>
              <p className="text-xs text-red-500 text-center">{message}</p>
            </motion.div>
          )}

          {status === 'idle' && (
            <motion.div
              key="idle"
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="flex flex-col items-center gap-2"
            >
              <svg className="w-8 h-8 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.338-2.32 5.75 5.75 0 011.344 11.096" />
              </svg>
              <p className="text-sm font-medium text-teal-700">
                {isDragging ? 'Drop to upload' : 'Drop PDFs or click to browse'}
              </p>
              <p className="text-xs text-teal-500">Multiple PDFs supported</p>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
