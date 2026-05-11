import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { deleteDocument } from '../api';

function formatRelativeTime(ts) {
  if (ts == null) return null;
  const seconds = Math.max(0, Math.floor(Date.now() / 1000 - ts));
  if (seconds < 60) return 'just now';
  const mins = Math.floor(seconds / 60);
  if (mins < 60) return `${mins} minute${mins === 1 ? '' : 's'} ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} hour${hours === 1 ? '' : 's'} ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days} day${days === 1 ? '' : 's'} ago`;
  return new Date(ts * 1000).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

function DocumentItem({ doc, onDeleted, isFresh, isSelected, onToggleSelected }) {
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

  const handleToggle = (e) => {
    e.stopPropagation();
    onToggleSelected?.(doc.document_id);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -6 }}
      animate={
        isFresh
          ? {
              opacity: 1,
              y: 0,
              backgroundColor: ['rgba(99, 102, 241, 0)', 'rgba(99, 102, 241, 0.10)', 'rgba(99, 102, 241, 0)'],
              boxShadow: [
                '0 0 0 0 rgba(99, 102, 241, 0)',
                '0 0 16px 0 rgba(99, 102, 241, 0.45)',
                '0 0 0 0 rgba(99, 102, 241, 0)',
              ],
            }
          : { opacity: 1, y: 0 }
      }
      transition={isFresh ? { duration: 2, ease: 'easeOut' } : { duration: 0.2 }}
      exit={{ opacity: 0, y: -6 }}
      className={`relative group flex items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-stone-100 transition-all duration-150 ${isSelected === false ? 'opacity-40' : ''}`}
    >
      <button
        onClick={handleToggle}
        aria-label={isSelected === false ? `Include ${doc.file_name} in search` : `Exclude ${doc.file_name} from search`}
        title={isSelected === false ? 'Excluded from search' : 'Included in search'}
        className="shrink-0 cursor-pointer rounded p-0.5 -m-0.5 hover:bg-stone-200/60 transition-colors"
      >
        {isSelected === false ? (
          <svg className="w-3.5 h-3.5 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3.98 8.223A10.477 10.477 0 001.934 12C3.226 16.338 7.244 19.5 12 19.5c.993 0 1.953-.138 2.863-.395M6.228 6.228A10.45 10.45 0 0112 4.5c4.756 0 8.773 3.162 10.065 7.498a10.523 10.523 0 01-4.293 5.774M6.228 6.228L3 3m3.228 3.228l3.65 3.65m7.244 7.244L21 21m-3.878-3.878l-3.65-3.65m0 0a3 3 0 10-4.243-4.243m4.242 4.242L9.88 9.88" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07.431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8.573-3.007-9.963-7.178z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        )}
      </button>
      <p className="flex-1 text-[13px] text-zinc-700 truncate">{doc.file_name}</p>
      {(doc.chunk_count != null || doc.indexed_at != null) && (
        <span
          role="tooltip"
          className="pointer-events-none absolute left-1/2 top-full z-30 mt-1 w-max max-w-[220px] -translate-x-1/2 rounded-lg border border-stone-200 bg-white px-2.5 py-1.5 text-[11px] font-mono text-zinc-600 shadow-lg opacity-0 group-hover:opacity-100 transition-opacity duration-150"
        >
          <span className="block truncate font-sans text-zinc-700">{doc.file_name}</span>
          {doc.chunk_count != null && <>{doc.chunk_count} chunk{doc.chunk_count === 1 ? '' : 's'}</>}
          {doc.chunk_count != null && doc.indexed_at != null && ' · '}
          {doc.indexed_at != null && <>indexed {formatRelativeTime(doc.indexed_at)}</>}
        </span>
      )}
      <button
        onClick={handleDelete}
        disabled={isDeleting}
        aria-label={confirmDelete ? 'Confirm delete' : `Delete ${doc.file_name}`}
        className={`shrink-0 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-all duration-150 p-0.5 rounded cursor-pointer ${
          confirmDelete ? 'opacity-100 text-red-600 hover:text-red-700' : 'text-zinc-400 hover:text-red-500'
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

function PendingItem({ item }) {
  const isIndexing = item.phase === 'indexing';
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -6 }}
      className="flex items-center gap-2 rounded-lg px-2 py-1.5"
    >
      <svg className="shrink-0 w-3.5 h-3.5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
      <div className="flex-1 min-w-0">
        <p className="text-[13px] text-zinc-700 truncate" title={item.file_name}>{item.file_name}</p>
        <div className="mt-0.5 flex items-center gap-1.5">
          {isIndexing ? (
            <>
              <div className="flex-1 h-0.5 bg-indigo-100 rounded-full overflow-hidden relative">
                <div className="absolute inset-y-0 w-1/3 bg-gradient-to-r from-transparent via-indigo-500 to-transparent animate-shimmer" />
              </div>
              <span className="text-[10px] font-mono text-indigo-500">indexing…</span>
            </>
          ) : (
            <>
              <div className="flex-1 h-0.5 bg-stone-200 rounded-full overflow-hidden">
                <div className="h-full bg-indigo-500 transition-all duration-150 ease-out" style={{ width: `${item.progress}%` }} />
              </div>
              <span className="text-[10px] font-mono text-zinc-500 tabular-nums">{item.progress}%</span>
            </>
          )}
        </div>
      </div>
    </motion.div>
  );
}

export default function DocumentList({ documents, onDocumentDeleted, isLoading, freshIds, pendingUploads = [], selectedIds, onToggleSelected }) {
  if (isLoading) {
    return (
      <div className="space-y-1">
        {[1, 2].map(i => (
          <div key={i} className="h-7 rounded-md bg-stone-100 animate-pulse" />
        ))}
      </div>
    );
  }

  if (documents.length === 0 && pendingUploads.length === 0) {
    return (
      <p className="text-[12px] text-zinc-400 px-2 py-1">No documents yet.</p>
    );
  }

  const selectedCount = selectedIds ? documents.filter(d => selectedIds.has(d.document_id)).length : documents.length;
  const showScopeFooter = selectedIds && documents.length > 0 && selectedCount < documents.length;

  return (
    <div className="space-y-0.5">
      <AnimatePresence>
        {pendingUploads.map(item => (
          <PendingItem key={item.id} item={item} />
        ))}
        {documents.map(doc => (
          <DocumentItem
            key={doc.document_id}
            doc={doc}
            onDeleted={onDocumentDeleted}
            isFresh={freshIds?.has(doc.document_id)}
            isSelected={selectedIds ? selectedIds.has(doc.document_id) : true}
            onToggleSelected={onToggleSelected}
          />
        ))}
      </AnimatePresence>
      {showScopeFooter && (
        <p className="mt-2 px-2 text-[11px] text-zinc-500 font-mono">
          Searching {selectedCount} of {documents.length} documents
        </p>
      )}
    </div>
  );
}
