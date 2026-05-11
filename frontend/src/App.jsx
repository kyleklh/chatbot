import { useState, useEffect, useCallback, useMemo, lazy, Suspense } from 'react';
import { getDocuments } from './api';
import UploadZone from './components/UploadZone';
import DocumentList from './components/DocumentList';
import ChatPanel from './components/ChatPanel';
import SourcesPanel from './components/SourcesPanel';
import ConversationsList from './components/ConversationsList';
import {
  loadConversations,
  saveConversations,
  loadActiveConversationId,
  saveActiveConversationId,
  newConversation,
  autoTitle,
} from './storage';

const PdfViewer = lazy(() => import('./components/PdfViewer'));

function ensureAtLeastOne(conversations) {
  if (conversations.length > 0) return conversations;
  return [newConversation()];
}

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [sources, setSources] = useState([]);
  const [freshIds, setFreshIds] = useState(() => new Set());
  const [viewingSource, setViewingSource] = useState(null);
  const [pendingUploads, setPendingUploads] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState(() => new Set());

  const [{ initialConversations, initialActiveId }] = useState(() => {
    const convs = ensureAtLeastOne(loadConversations());
    const stored = loadActiveConversationId();
    const activeId = stored && convs.some(c => c.id === stored) ? stored : convs[0].id;
    return { initialConversations: convs, initialActiveId: activeId };
  });
  const [conversations, setConversations] = useState(initialConversations);
  const [activeConvId, setActiveConvId] = useState(initialActiveId);

  const activeConv = useMemo(
    () => conversations.find(c => c.id === activeConvId) || conversations[0],
    [conversations, activeConvId],
  );

  useEffect(() => { saveConversations(conversations); }, [conversations]);
  useEffect(() => { saveActiveConversationId(activeConvId); }, [activeConvId]);

  useEffect(() => {
    getDocuments()
      .then(data => {
        const docs = data.documents || [];
        setDocuments(docs);
        setSelectedDocIds(new Set(docs.map(d => d.document_id)));
      })
      .catch(console.error)
      .finally(() => setIsLoadingDocs(false));
  }, []);

  const handleDocumentUploaded = (doc) => {
    setDocuments(prev => {
      const exists = prev.some(d => d.document_id === doc.document_id);
      return exists ? prev : [...prev, { document_id: doc.document_id, file_name: doc.file_name }];
    });
    setSelectedDocIds(prev => new Set(prev).add(doc.document_id));
    setFreshIds(prev => new Set(prev).add(doc.document_id));
    setTimeout(() => {
      setFreshIds(prev => {
        const next = new Set(prev);
        next.delete(doc.document_id);
        return next;
      });
    }, 2200);
  };

  const handleDocumentDeleted = (documentId) => {
    setDocuments(prev => prev.filter(d => d.document_id !== documentId));
    setSelectedDocIds(prev => {
      const next = new Set(prev);
      next.delete(documentId);
      return next;
    });
  };

  const toggleDocSelected = (documentId) => {
    setSelectedDocIds(prev => {
      const next = new Set(prev);
      if (next.has(documentId)) next.delete(documentId);
      else next.add(documentId);
      return next;
    });
  };

  const queryDocumentIds = selectedDocIds.size === documents.length || documents.length === 0
    ? null
    : Array.from(selectedDocIds);

  const handleAnswer = (newSources) => {
    setSources(newSources || []);
  };

  const handleViewSource = (src) => {
    if (!src?.document_id) return;
    setViewingSource(src);
  };

  // Stable setter that updates the active conversation's messages.
  const setActiveMessages = useCallback((updater) => {
    setConversations(prev => prev.map(c => {
      if (c.id !== activeConvId) return c;
      const nextMessages = typeof updater === 'function' ? updater(c.messages) : updater;
      let title = c.title;
      // Auto-title on first user message
      if (title === 'New chat') {
        const firstUser = nextMessages.find(m => m.type === 'user');
        if (firstUser?.text) title = autoTitle(firstUser.text);
      }
      return { ...c, messages: nextMessages, updatedAt: Date.now(), title };
    }));
  }, [activeConvId]);

  const selectConversation = (id) => {
    if (id === activeConvId) return;
    setActiveConvId(id);
    const conv = conversations.find(c => c.id === id);
    const lastAssistant = [...(conv?.messages || [])].reverse().find(m => m.type === 'assistant' && m.sources?.length);
    setSources(lastAssistant?.sources || []);
  };

  const renameConversation = (id, title) => {
    setConversations(prev => prev.map(c => c.id === id ? { ...c, title, updatedAt: Date.now() } : c));
  };

  const deleteConversation = (id) => {
    setConversations(prev => {
      const remaining = prev.filter(c => c.id !== id);
      const next = ensureAtLeastOne(remaining);
      if (id === activeConvId) {
        setActiveConvId(next[0].id);
        setSources([]);
      }
      return next;
    });
  };

  const handleNewChat = () => {
    if (activeConv && activeConv.messages.length === 0) return; // already on a fresh chat
    const conv = newConversation();
    setConversations(prev => [conv, ...prev]);
    setActiveConvId(conv.id);
    setSources([]);
  };

  return (
    <div className="flex h-screen bg-stone-50 text-zinc-900">
      {/* Left rail */}
      <aside className="w-60 shrink-0 border-r border-stone-200 bg-white flex flex-col">
        {/* Brand */}
        <div className="shrink-0 flex items-center gap-2.5 px-4 h-14 border-b border-stone-200">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center shadow-sm shadow-indigo-500/30">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <span className="text-[15px] font-semibold tracking-tight text-zinc-900">DocuRAG</span>
        </div>

        {/* Conversations */}
        <div className="shrink-0 max-h-[45%] flex flex-col px-3 py-3 border-b border-stone-200 overflow-hidden">
          <div className="overflow-y-auto -mx-1 px-1">
            <ConversationsList
              conversations={conversations}
              activeId={activeConvId}
              onSelect={selectConversation}
              onRename={renameConversation}
              onDelete={deleteConversation}
              onNewChat={handleNewChat}
            />
          </div>
        </div>

        {/* Upload */}
        <div className="shrink-0 px-3 py-3 border-b border-stone-200">
          <UploadZone
            onDocumentUploaded={handleDocumentUploaded}
            onPendingChange={setPendingUploads}
          />
        </div>

        {/* Document list */}
        <div className="flex-1 flex flex-col overflow-hidden px-3 py-3 min-h-0">
          <div className="flex items-center justify-between mb-2 px-1">
            <p className="text-[11px] font-semibold text-zinc-500 uppercase tracking-wider">Documents</p>
            {documents.length > 0 && (
              <span className="text-[11px] font-medium text-zinc-400 font-mono">{documents.length}</span>
            )}
          </div>
          <div className="flex-1 overflow-y-auto -mx-1 px-1">
            <DocumentList
              documents={documents}
              onDocumentDeleted={handleDocumentDeleted}
              isLoading={isLoadingDocs}
              freshIds={freshIds}
              pendingUploads={pendingUploads}
              selectedIds={selectedDocIds}
              onToggleSelected={toggleDocSelected}
            />
          </div>
        </div>
      </aside>

      {/* Center: chat */}
      <main className="flex-1 flex flex-col overflow-hidden min-w-0">
        <ChatPanel
          key={activeConvId}
          messages={activeConv?.messages || []}
          onMessagesChange={setActiveMessages}
          onAnswer={handleAnswer}
          hasDocuments={documents.length > 0}
          onViewSource={handleViewSource}
          queryDocumentIds={queryDocumentIds}
        />
      </main>

      {/* Right: sources — hidden until there are docs to query */}
      {documents.length > 0 && (
        <aside className="w-96 shrink-0 hidden xl:flex flex-col border-l border-stone-200 bg-stone-50">
          <SourcesPanel sources={sources} />
        </aside>
      )}

      {viewingSource && (
        <Suspense fallback={null}>
          <PdfViewer source={viewingSource} onClose={() => setViewingSource(null)} />
        </Suspense>
      )}
    </div>
  );
}
