import { useState, useEffect } from 'react';
import { getDocuments } from './api';
import UploadZone from './components/UploadZone';
import DocumentList from './components/DocumentList';
import ChatPanel from './components/ChatPanel';

export default function App() {
  const [documents, setDocuments] = useState([]);
  const [selectedDoc, setSelectedDoc] = useState(null);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  useEffect(() => {
    getDocuments()
      .then(data => setDocuments(data.documents || []))
      .catch(console.error)
      .finally(() => setIsLoadingDocs(false));
  }, []);

  const handleDocumentUploaded = (result) => {
    const doc = { document_id: result.document_id, file_name: result.file_name };
    setDocuments(prev => [...prev, doc]);
    setSelectedDoc(doc);
    setSidebarOpen(false);
  };

  const handleDocumentDeleted = (documentId) => {
    setDocuments(prev => prev.filter(d => d.document_id !== documentId));
    if (selectedDoc?.document_id === documentId) setSelectedDoc(null);
  };

  const handleSelectDoc = (doc) => {
    setSelectedDoc(doc);
    setSidebarOpen(false);
  };

  return (
    <div className="flex h-screen bg-teal-50 overflow-hidden">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/20 backdrop-blur-sm z-20 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed inset-y-0 left-0 z-30 w-72 flex flex-col bg-white/80 backdrop-blur-md border-r border-teal-100 shadow-xl shadow-teal-100/50
        transform transition-transform duration-300 ease-in-out
        md:relative md:translate-x-0 md:shadow-none md:z-auto
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}
      `}>
        {/* Logo */}
        <div className="shrink-0 flex items-center gap-3 px-5 py-5 border-b border-teal-100">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-teal-500 to-teal-700 flex items-center justify-center shadow-md shadow-teal-200">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <div>
            <h1 className="text-base font-bold text-teal-900 leading-none">DocuRAG</h1>
            <p className="text-xs text-teal-500 mt-0.5">AI Document Assistant</p>
          </div>
          <button
            onClick={() => setSidebarOpen(false)}
            className="ml-auto p-1.5 rounded-lg hover:bg-teal-50 text-teal-400 cursor-pointer md:hidden"
            aria-label="Close sidebar"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          <UploadZone onDocumentUploaded={handleDocumentUploaded} />

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-xs font-semibold text-teal-700 uppercase tracking-wider">Documents</p>
              <span className="text-xs text-teal-500 font-medium">{documents.length}</span>
            </div>
            <DocumentList
              documents={documents}
              selectedDoc={selectedDoc}
              onSelectDoc={handleSelectDoc}
              onDocumentDeleted={handleDocumentDeleted}
              isLoading={isLoadingDocs}
            />
          </div>
        </div>

        {/* Footer */}
        <div className="shrink-0 px-5 py-3 border-t border-teal-100">
          <p className="text-xs text-teal-400 text-center">Powered by Groq + ChromaDB</p>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 flex flex-col overflow-hidden min-w-0">
        {/* Mobile header */}
        <div className="md:hidden shrink-0 flex items-center gap-3 px-4 py-3 bg-white/80 backdrop-blur-sm border-b border-teal-100">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 rounded-lg hover:bg-teal-50 text-teal-600 cursor-pointer"
            aria-label="Open sidebar"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12" />
            </svg>
          </button>
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-teal-500 to-teal-700 flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
              </svg>
            </div>
            <span className="text-sm font-bold text-teal-900">DocuRAG</span>
          </div>
        </div>

        <ChatPanel selectedDoc={selectedDoc} />
      </main>
    </div>
  );
}
