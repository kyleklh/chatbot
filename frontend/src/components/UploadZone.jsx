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
      setTimeout(() => { setStatus('idle'); setFileResults([]); }, 6000);
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
    ? 'border-cyan-500 bg-cyan-50'
    : status === 'error'
    ? 'border-red-300 bg-red-50'
    : status === 'success'
    ? 'border-emerald-300 bg-emerald-50'
    : 'border-slate-300 bg-white hover:border-slate-400 hover:bg-slate-50';

  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Upload PDFs</p>
      <motion.div
        animate={isDragging ? { scale: 1.01 } : { scale: 1 }}
        transition={{ duration: 0.15 }}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={onDrop}
        onClick={() => status !== 'uploading' && inputRef.current?.click()}
        className={`cursor-pointer rounded-xl border-2 border-dashed p-5 text-center transition-colors duration-150 ${borderStyle}`}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => e.key === 'Enter' && inputRef.current?.click()}
      >
        <input ref={inputRef} type="file" accept=".pdf" multiple className="sr-only" onChange={onInputChange} />

        <AnimatePresence mode="wait">
          {status === 'uploading' && (
            <motion.div key="uploading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-2">
              <svg className="w-7 h-7 text-cyan-500 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              <p className="text-sm font-medium text-slate-700">Processing…</p>
            </motion.div>
          )}
          {status === 'success' && (
            <motion.div key="success" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-2 w-full">
              <p className="text-sm font-medium text-slate-700">{message}</p>
              {fileResults.length > 0 && (
                <div className="w-full space-y-1 max-h-28 overflow-y-auto text-left">
                  {fileResults.map((f, i) => (
                    <div key={i} className="flex items-center gap-2 text-xs">
                      {f.status === 'error' ? (
                        <svg className="w-3.5 h-3.5 shrink-0 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      ) : (
                        <svg className="w-3.5 h-3.5 shrink-0 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                      <span className={`truncate ${f.status === 'error' ? 'text-red-600' : 'text-slate-600'}`}>
                        {f.file_name}{f.status === 'error' ? ` — ${f.error}` : ''}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}
          {status === 'error' && (
            <motion.div key="error" initial={{ opacity: 0, y: 4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-1">
              <svg className="w-7 h-7 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <p className="text-sm font-medium text-red-600">Failed</p>
              <p className="text-xs text-red-500">{message}</p>
            </motion.div>
          )}
          {status === 'idle' && (
            <motion.div key="idle" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center gap-2">
              <svg className="w-7 h-7 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.338-2.32 5.75 5.75 0 011.344 11.096" />
              </svg>
              <p className="text-sm font-medium text-slate-700">
                {isDragging ? 'Drop to upload' : 'Drop PDFs or click to browse'}
              </p>
              <p className="text-xs text-slate-400">Multiple files supported</p>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
}
