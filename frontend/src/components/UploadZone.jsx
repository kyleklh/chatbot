import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { uploadDocument } from '../api';

export default function UploadZone({ onDocumentUploaded }) {
  const [isDragging, setIsDragging] = useState(false);
  const [status, setStatus] = useState('idle');
  const [message, setMessage] = useState('');
  const [fileResults, setFileResults] = useState([]);
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
      const docs = result.documents || [result];
      const succeeded = docs.filter(d => d.status === 'ok' || !d.status);
      const failed = docs.filter(d => d.status === 'error');
      setFileResults(docs);
      setStatus(failed.length > 0 && succeeded.length === 0 ? 'error' : 'success');
      setMessage(`${succeeded.length}/${docs.length} indexed`);
      succeeded.forEach(doc => onDocumentUploaded(doc));
      setTimeout(() => { setStatus('idle'); setFileResults([]); }, 5000);
    } catch (err) {
      setStatus('error');
      setMessage(err.message);
      setTimeout(() => { setStatus('idle'); setFileResults([]); }, 4000);
    }
  };

  const onDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (status === 'uploading') return;
    handleFiles(e.dataTransfer.files);
  };

  const onInputChange = (e) => {
    handleFiles(e.target.files);
    e.target.value = '';
  };

  const borderStyle = isDragging
    ? 'border-indigo-400 bg-indigo-50'
    : status === 'error'
    ? 'border-red-300 bg-red-50'
    : status === 'success'
    ? 'border-emerald-300 bg-emerald-50'
    : status === 'uploading'
    ? 'border-indigo-300 bg-indigo-50/50'
    : 'border-stone-300 bg-stone-50/50 hover:border-stone-400 hover:bg-stone-100/50';

  return (
    <motion.div
      animate={isDragging ? { scale: 1.01 } : { scale: 1 }}
      transition={{ duration: 0.15 }}
      onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={onDrop}
      onClick={() => status !== 'uploading' && inputRef.current?.click()}
      className={`${status !== 'uploading' ? 'cursor-pointer' : 'cursor-default'} rounded-lg border-2 border-dashed p-3 text-center transition-colors duration-150 ${borderStyle}`}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && status !== 'uploading' && inputRef.current?.click()}
    >
      <input ref={inputRef} type="file" accept=".pdf" multiple className="sr-only" onChange={onInputChange} />

      <AnimatePresence mode="wait">
        {status === 'uploading' && (
          <motion.div key="uploading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-2 py-1 w-full">
            <p className="text-[12px] font-medium text-indigo-700">Indexing…</p>
            <div className="w-full h-1 bg-indigo-100 rounded-full overflow-hidden relative">
              <div className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-indigo-500 to-transparent animate-shimmer" />
            </div>
            <p className="text-[10px] font-mono text-indigo-500/70">extract → chunk → embed</p>
          </motion.div>
        )}
        {status === 'success' && (
          <motion.div key="success" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-1 w-full py-1">
            <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
            </svg>
            <p className="text-[12px] font-medium text-zinc-700">{message}</p>
          </motion.div>
        )}
        {status === 'error' && (
          <motion.div key="error" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-1 py-1">
            <svg className="w-5 h-5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-[12px] font-medium text-red-600 truncate max-w-full">{message}</p>
          </motion.div>
        )}
        {status === 'idle' && (
          <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-1 py-1">
            <svg className="w-5 h-5 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.338-2.32 5.75 5.75 0 011.344 11.096" />
            </svg>
            <p className="text-[12px] font-medium text-zinc-600">
              {isDragging ? 'Drop to upload' : 'Drop PDF or click'}
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
