import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { deleteDocument } from '../api';

function DocumentItem({ doc, isSelected, onSelect, onDeleted }) {
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
      initial={{ opacity: 0, x: -12 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -12 }}
      onClick={() => onSelect(doc)}
      className={`group relative flex items-center gap-3 rounded-xl px-3 py-2.5 cursor-pointer transition-colors duration-150 ${
        isSelected
          ? 'bg-teal-600 text-white shadow-md shadow-teal-200'
          : 'bg-white/60 hover:bg-teal-50 text-teal-900 border border-teal-100'
      }`}
    >
      <div className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${isSelected ? 'bg-white/20' : 'bg-teal-100'}`}>
        <svg className={`w-4 h-4 ${isSelected ? 'text-white' : 'text-teal-600'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
      </div>

      <p className={`flex-1 text-sm font-medium truncate ${isSelected ? 'text-white' : 'text-teal-900'}`}>
        {doc.file_name}
      </p>

      <button
        onClick={handleDelete}
        disabled={isDeleting}
        aria-label={confirmDelete ? 'Confirm delete' : `Delete ${doc.file_name}`}
        className={`shrink-0 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all duration-150 p-1 rounded-lg cursor-pointer ${
          confirmDelete
            ? 'opacity-100 bg-red-500 text-white'
            : isSelected
            ? 'hover:bg-white/20 text-white/70 hover:text-white'
            : 'hover:bg-red-50 text-teal-400 hover:text-red-500'
        }`}
      >
        {isDeleting ? (
          <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
          </svg>
        ) : confirmDelete ? (
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
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

export default function DocumentList({ documents, selectedDoc, onSelectDoc, onDocumentDeleted, isLoading }) {
  if (isLoading) {
    return (
      <div className="space-y-2">
        {[1, 2].map(i => (
          <div key={i} className="h-12 rounded-xl bg-teal-100/60 animate-pulse" />
        ))}
      </div>
    );
  }

  if (documents.length === 0) {
    return (
      <motion.div
        initial={{ opacity: 0 }} animate={{ opacity: 1 }}
        className="flex flex-col items-center gap-2 py-6 text-center"
      >
        <div className="w-12 h-12 rounded-full bg-teal-100 flex items-center justify-center">
          <svg className="w-6 h-6 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
        </div>
        <p className="text-sm font-medium text-teal-700">No documents yet</p>
        <p className="text-xs text-teal-500">Upload a PDF to get started</p>
      </motion.div>
    );
  }

  return (
    <div className="space-y-1.5">
      <AnimatePresence>
        {documents.map(doc => (
          <DocumentItem
            key={doc.document_id}
            doc={doc}
            isSelected={selectedDoc?.document_id === doc.document_id}
            onSelect={onSelectDoc}
            onDeleted={onDocumentDeleted}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}
