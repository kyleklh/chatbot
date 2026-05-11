import { useState, useEffect, lazy, Suspense } from 'react';
import { getDocuments } from './api';
import UploadZone from './components/UploadZone';
import DocumentList from './components/DocumentList';
import ChatPanel from './components/ChatPanel';
import SourcesPanel from './components/SourcesPanel';

const PdfViewer = lazy(() => import('./components/PdfViewer'));

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [sources, setSources] = useState([]);
  const [freshIds, setFreshIds] = useState(() => new Set());
  const [viewingSource, setViewingSource] = useState(null);

  useEffect(() => {
    getDocuments()
      .then(data => setDocuments(data.documents || []))
      .catch(console.error)
      .finally(() => setIsLoadingDocs(false));
  }, []);

  const handleDocumentUploaded = (doc) => {
    setDocuments(prev => {
      const exists = prev.some(d => d.document_id === doc.document_id);
      return exists ? prev : [...prev, { document_id: doc.document_id, file_name: doc.file_name }];
    });
    // Mark as fresh for ~2s pulse
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
  };

  const handleAnswer = (newSources) => {
    setSources(newSources || []);
  };

  const handleCitationClick = (idx) => {
    if (idx == null || idx < 0 || idx >= sources.length) return;
    const src = sources[idx];
    if (!src?.document_id) return;
    setViewingSource(src);
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

        {/* Upload */}
        <div className="px-3 py-3 border-b border-stone-200">
          <UploadZone onDocumentUploaded={handleDocumentUploaded} />
        </div>

        {/* Document list */}
        <div className="flex-1 flex flex-col overflow-hidden px-3 py-3">
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
            />
          </div>
        </div>
      </aside>

      {/* Center: chat */}
      <main className="flex-1 flex flex-col overflow-hidden min-w-0">
        <ChatPanel
          onAnswer={handleAnswer}
          hasDocuments={documents.length > 0}
          sources={sources}
          onCitationClick={handleCitationClick}
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
