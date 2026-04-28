import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { deleteDocument } from '../api';

function DocumentItem({ doc, onDeleted }) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const handleDelete = async (e) => {
    e.stopPropagation();
    if (!confirmDelete) {
      setConfirmDelete(true);
      setTimeout(() => setConfirmDelete(false), 3000);
      return;
    }
    setIsDeleting(true);
    try {
      await deleteDocument(doc.document_id);
      onDeleted(doc.document_id);
    } catch {
      setIsDeleting(false);
      setConfirmDelete(false);
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      className="group flex items-center gap-2.5 rounded-lg px-3 py-2 bg-white border border-slate-200 hover:border-slate-300 transition-colors duration-150"
    >
      <svg className="shrink-0 w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
      <p className="flex-1 text-sm text-slate-700 truncate">{doc.file_name}</p>
      <button
        onClick={handleDelete}
        disabled={isDeleting}
        aria-label={confirmDelete ? 'Confirm delete' : `Delete ${doc.file_name}`}
        className={`shrink-0 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all duration-150 p-1 rounded cursor-pointer ${
          confirmDelete ? 'opacity-100 text-red-600 hover:text-red-700' : 'text-slate-400 hover:text-red-500'
        }`}
      >
        {isDeleting ? (
          <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
          </svg>
        )}
      </button>
    </motion.div>
  );
}

export default function DocumentList({ documents, onDocumentDeleted, isLoading }) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2].map(i => (
          <div key={i} className="h-10 rounded-lg bg-slate-100 animate-pulse" />
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <p className="text-sm text-slate-400 py-3">No documents yet — upload a PDF above.</p>
    );
  }

  return (
    <div className="space-y-1.5 max-h-48 overflow-y-auto">
      <AnimatePresence>
        {documents.map(doc => (
          <DocumentItem
            key={doc.document_id}
            doc={doc}
            onDeleted={onDocumentDeleted}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}
