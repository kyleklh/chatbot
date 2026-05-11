import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { groupByDate } from '../storage';

function ConversationItem({ conversation, isActive, onSelect, onRename, onDelete }) {
  const [renaming, setRenaming] = useState(false);
  const [draft, setDraft] = useState(conversation.title);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const inputRef = useRef(null);

  useEffect(() => {
    if (renaming) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [renaming]);

  const commit = () => {
    const trimmed = draft.trim();
    if (trimmed && trimmed !== conversation.title) onRename(conversation.id, trimmed);
    setRenaming(false);
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    if (!confirmDelete) {
      setConfirmDelete(true);
      setTimeout(() => setConfirmDelete(false), 3000);
      return;
    }
    onDelete(conversation.id);
  };

  const startRename = (e) => {
    e.stopPropagation();
    setDraft(conversation.title);
    setRenaming(true);
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      onClick={() => !renaming && onSelect(conversation.id)}
      className={`group flex items-center gap-1.5 rounded-lg px-2 py-1.5 cursor-pointer transition-colors duration-150 ${
        isActive ? 'bg-indigo-50 hover:bg-indigo-50' : 'hover:bg-stone-100'
      }`}
    >
      <svg className={`shrink-0 w-3.5 h-3.5 ${isActive ? 'text-indigo-500' : 'text-zinc-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
      {renaming ? (
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === 'Enter') commit();
            else if (e.key === 'Escape') { setDraft(conversation.title); setRenaming(false); }
          }}
          onClick={(e) => e.stopPropagation()}
          className="flex-1 min-w-0 bg-transparent outline-none border-b border-indigo-300 text-[13px] text-zinc-800"
        />
      ) : (
        <p className={`flex-1 text-[13px] truncate ${isActive ? 'text-indigo-700 font-medium' : 'text-zinc-700'}`}>
          {conversation.title}
        </p>
      )}
      <div className="shrink-0 flex items-center gap-0.5 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity duration-150">
        <button
          onClick={startRename}
          aria-label={`Rename ${conversation.title}`}
          title="Rename"
          className="p-0.5 rounded cursor-pointer text-zinc-400 hover:text-zinc-700 hover:bg-stone-200/60"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 112.652 2.652L10.582 16.07a4.5 4.5 0 01-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 011.13-1.897l8.932-8.931z" />
          </svg>
        </button>
        <button
          onClick={handleDelete}
          aria-label={confirmDelete ? `Confirm delete ${conversation.title}` : `Delete ${conversation.title}`}
          title={confirmDelete ? 'Click again to confirm' : 'Delete'}
          className={`p-0.5 rounded cursor-pointer ${
            confirmDelete ? 'text-red-600 hover:text-red-700' : 'text-zinc-400 hover:text-red-500 hover:bg-stone-200/60'
          }`}
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
          </svg>
        </button>
      </div>
    </motion.div>
  );
}

export default function ConversationsList({ conversations, activeId, onSelect, onRename, onDelete, onNewChat }) {
  const groups = groupByDate(conversations);
  const labels = ['Today', 'Yesterday', 'Last 7 days', 'Older'];
  const isEmpty = conversations.length === 0;

  return (
    <div className="flex flex-col gap-1">
      <button
        onClick={onNewChat}
        className="flex items-center gap-2 rounded-lg px-2 py-1.5 cursor-pointer text-[13px] font-medium text-indigo-700 bg-indigo-50/70 hover:bg-indigo-100 transition-colors duration-150"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
        New chat
      </button>
      {isEmpty ? (
        <p className="px-2 py-1 text-[12px] text-zinc-400">No conversations yet.</p>
      ) : (
        <div className="space-y-1.5">
          <AnimatePresence>
            {labels.map(label => {
              const items = groups[label];
              if (!items || items.length === 0) return null;
              return (
                <div key={label} className="space-y-0.5">
                  <p className="px-2 pt-1 text-[10px] font-semibold text-zinc-400 uppercase tracking-wider">{label}</p>
                  {items.map(c => (
                    <ConversationItem
                      key={c.id}
                      conversation={c}
                      isActive={c.id === activeId}
                      onSelect={onSelect}
                      onRename={onRename}
                      onDelete={onDelete}
                    />
                  ))}
                </div>
              );
            })}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
