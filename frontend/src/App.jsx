import { useState, useEffect } from 'react';
import { getDocuments } from './api';
import UploadZone from './components/UploadZone';
import DocumentList from './components/DocumentList';
import ChatPanel from './components/ChatPanel';
import SourcesPanel from './components/SourcesPanel';

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [sources, setSources] = useState([]);
  const [showManage, setShowManage] = useState(false);

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
  };

  const handleDocumentDeleted = (documentId) => {
    setDocuments(prev => prev.filter(d => d.document_id !== documentId));
  };

  const handleAnswer = (newSources) => {
    setSources(newSources || []);
  };

  return (
    <div className="flex flex-col h-screen bg-slate-50" style={{ fontFamily: 'Inter, sans-serif' }}>
      {/* Header */}
      <header className="shrink-0 flex items-center gap-4 px-5 py-3 bg-white border-b border-slate-200">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-cyan-600 flex items-center justify-center">
            <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <span className="text-sm font-semibold text-slate-900">DocuRAG</span>
        </div>

        <div className="flex items-center gap-2 ml-auto">
          {documents.length > 0 && (
            <span className="text-xs text-slate-500 font-medium">
              {documents.length} doc{documents.length !== 1 ? 's' : ''} indexed
            </span>
          )}
          <button
            onClick={() => setShowManage(v => !v)}
            className="flex items-center gap-1.5 text-sm font-medium px-3 py-1.5 rounded-lg bg-cyan-600 text-white hover:bg-cyan-700 transition-colors duration-150 cursor-pointer"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
            </svg>
            Upload
          </button>
        </div>
      </header>

      {/* Upload / Manage panel (slide-down) */}
      {showManage && (
        <div className="shrink-0 bg-white border-b border-slate-200 px-5 py-4">
          <div className="max-w-4xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-5">
            <UploadZone onDocumentUploaded={(doc) => { handleDocumentUploaded(doc); }} />
            <div className="space-y-2">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Indexed Documents</p>
              <DocumentList
                documents={documents}
                onDocumentDeleted={handleDocumentDeleted}
                isLoading={isLoadingDocs}
              />
            </div>
          </div>
        </div>
      )}

      {/* Body: chat + sources */}
      <div className="flex flex-1 overflow-hidden">
        <div className="flex-1 flex flex-col overflow-hidden border-r border-slate-200">
          <ChatPanel
            onAnswer={handleAnswer}
            hasDocuments={documents.length > 0}
            onUploadClick={() => setShowManage(true)}
          />
        </div>
        <div className="w-96 shrink-0 hidden lg:flex flex-col overflow-hidden">
          <SourcesPanel sources={sources} />
        </div>
      </div>
    </div>
  );
}
