import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';

function CitationBadge({ num }) {
  return (
    <sup className="text-teal-600 font-semibold text-[10px] mx-0.5">
      [{num}]
    </sup>
  );
}

function renderWithCitations(children) {
  const process = (node) => {
    if (typeof node !== 'string') return node;
    // Match [N] or [Source N] — single digit or multi
    const parts = node.split(/(\[(?:Source )?\d+\])/g);
    if (parts.length === 1) return node;
    return parts.map((part, i) => {
      const match = part.match(/\[(?:Source )?(\d+)\]/);
      return match ? <CitationBadge key={i} num={match[1]} /> : part;
    });
  };
  if (Array.isArray(children)) return children.map(process);
  return process(children);
}
import { sendChat } from '../api';
import SourceCard from './SourceCard';

function LoadingDots() {
  return (
    <div className="flex items-center gap-1 px-4 py-3">
      {[0, 1, 2].map(i => (
        <motion.span
          key={i}
          className="w-2 h-2 rounded-full bg-teal-400"
          animate={{ y: [0, -6, 0] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15, ease: 'easeInOut' }}
        />
      ))}
    </div>
  );
}

function UserMessage({ text }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex justify-end"
    >
      <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-teal-600 px-4 py-3 shadow-sm shadow-teal-200">
        <p className="text-sm leading-relaxed text-white">{text}</p>
      </div>
    </motion.div>
  );
}

function AssistantMessage({ text, sources }) {
  const [showSources, setShowSources] = useState(false);

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col gap-3"
    >
      <div className="flex gap-3 items-start">
        <div className="shrink-0 w-8 h-8 rounded-full bg-teal-600 flex items-center justify-center shadow-sm">
          <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
          </svg>
        </div>
        <div className="max-w-[80%] rounded-2xl rounded-tl-sm bg-white/80 backdrop-blur-sm border border-teal-100 px-4 py-3 shadow-sm prose prose-sm prose-teal max-w-none">
          <ReactMarkdown
            components={{
              p: ({ children }) => <p className="text-sm leading-relaxed text-teal-900 mb-2 last:mb-0">{renderWithCitations(children)}</p>,
              strong: ({ children }) => <strong className="font-semibold text-teal-900">{renderWithCitations(children)}</strong>,
              em: ({ children }) => <em className="italic text-teal-800">{children}</em>,
              ul: ({ children }) => <ul className="list-disc list-inside space-y-1 my-2 text-sm text-teal-900">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 my-2 text-sm text-teal-900">{children}</ol>,
              li: ({ children }) => <li className="text-sm leading-relaxed text-teal-900">{renderWithCitations(children)}</li>,
              code: ({ children }) => <code className="bg-teal-50 text-teal-800 rounded px-1 py-0.5 text-xs font-mono">{children}</code>,
              h1: ({ children }) => <h1 className="text-base font-bold text-teal-900 mb-1 mt-2">{children}</h1>,
              h2: ({ children }) => <h2 className="text-sm font-bold text-teal-900 mb-1 mt-2">{children}</h2>,
              h3: ({ children }) => <h3 className="text-sm font-semibold text-teal-900 mb-1 mt-2">{children}</h3>,
              blockquote: ({ children }) => <blockquote className="border-l-2 border-teal-300 pl-3 italic text-teal-700 my-2">{children}</blockquote>,
            }}
          >
            {text}
          </ReactMarkdown>
        </div>
      </div>

      {sources && sources.length > 0 && (
        <div className="ml-11">
          <button
            onClick={() => setShowSources(v => !v)}
            className="flex items-center gap-1.5 text-xs font-medium text-teal-600 hover:text-teal-800 cursor-pointer transition-colors duration-150 mb-2"
          >
            <svg className={`w-3.5 h-3.5 transition-transform duration-200 ${showSources ? 'rotate-90' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
            {showSources ? 'Hide' : 'Show'} {sources.length} source{sources.length !== 1 ? 's' : ''}
          </button>

          <AnimatePresence>
            {showSources && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-2 overflow-hidden"
              >
                {sources.map((source, i) => (
                  <SourceCard key={i} source={source} index={i} />
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </motion.div>
  );
}

function ErrorMessage({ text }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex gap-3 items-start"
    >
      <div className="shrink-0 w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
        <svg className="w-4 h-4 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <div className="rounded-2xl rounded-tl-sm bg-red-50 border border-red-100 px-4 py-3">
        <p className="text-sm text-red-700">{text}</p>
      </div>
    </motion.div>
  );
}

function EmptyChat() {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center h-full gap-4 text-center px-8"
    >
      <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-teal-500 to-teal-700 flex items-center justify-center shadow-lg shadow-teal-200">
        <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
        </svg>
      </div>
      <div>
        <h2 className="text-lg font-semibold text-teal-900">Ask anything about your document</h2>
        <p className="text-sm text-teal-600 mt-1 max-w-xs">
          Type a question below and DocuRAG will find the answer using your uploaded PDF.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-sm mt-2">
        {['What is this document about?', 'Summarize the key points', 'What are the main conclusions?', 'List the important dates'].map(q => (
          <div key={q} className="rounded-xl border border-teal-100 bg-white/60 px-3 py-2">
            <p className="text-xs text-teal-600 font-medium">{q}</p>
          </div>
        ))}
      </div>
    </motion.div>
  );
}

function NoDocSelected() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex flex-col items-center justify-center h-full gap-3 text-center px-8"
    >
      <div className="w-16 h-16 rounded-2xl bg-teal-100 flex items-center justify-center">
        <svg className="w-8 h-8 text-teal-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
        </svg>
      </div>
      <div>
        <h2 className="text-lg font-semibold text-teal-900">Select a document</h2>
        <p className="text-sm text-teal-600 mt-1 max-w-xs">
          Choose a document from the sidebar or upload a new PDF to start chatting.
        </p>
      </div>
    </motion.div>
  );
}

export default function ChatPanel({ selectedDoc }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const prevDocRef = useRef(null);

  useEffect(() => {
    if (prevDocRef.current && selectedDoc?.document_id !== prevDocRef.current) {
      setMessages([]);
    }
    prevDocRef.current = selectedDoc?.document_id;
  }, [selectedDoc]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async () => {
    const question = input.trim();
    if (!question || !selectedDoc || isLoading) return;

    setMessages(prev => [...prev, { type: 'user', text: question }]);
    setInput('');
    setIsLoading(true);
    textareaRef.current?.focus();

    try {
      const result = await sendChat(selectedDoc.document_id, question);
      setMessages(prev => [...prev, { type: 'assistant', text: result.answer, sources: result.sources }]);
    } catch (err) {
      setMessages(prev => [...prev, { type: 'error', text: err.message }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = input.trim().length > 0 && !!selectedDoc && !isLoading;

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Header */}
      <div className="shrink-0 flex items-center gap-3 px-6 py-4 border-b border-teal-100 bg-white/60 backdrop-blur-sm">
        {selectedDoc ? (
          <>
            <div className="w-8 h-8 rounded-lg bg-teal-100 flex items-center justify-center">
              <svg className="w-4 h-4 text-teal-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
              </svg>
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-teal-900 truncate">{selectedDoc.file_name}</p>
              <p className="text-xs text-teal-500">Active document</p>
            </div>
          </>
        ) : (
          <p className="text-sm font-medium text-teal-500">No document selected</p>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
        {!selectedDoc ? (
          <NoDocSelected />
        ) : messages.length === 0 ? (
          <EmptyChat />
        ) : (
          <>
            {messages.map((msg, i) => (
              msg.type === 'user' ? (
                <UserMessage key={i} text={msg.text} />
              ) : msg.type === 'assistant' ? (
                <AssistantMessage key={i} text={msg.text} sources={msg.sources} />
              ) : (
                <ErrorMessage key={i} text={msg.text} />
              )
            ))}
            {isLoading && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex gap-3 items-start"
              >
                <div className="shrink-0 w-8 h-8 rounded-full bg-teal-600 flex items-center justify-center shadow-sm">
                  <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                  </svg>
                </div>
                <div className="rounded-2xl rounded-tl-sm bg-white/80 backdrop-blur-sm border border-teal-100 shadow-sm">
                  <LoadingDots />
                </div>
              </motion.div>
            )}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      <div className="shrink-0 border-t border-teal-100 bg-white/60 backdrop-blur-sm px-6 py-4">
        <div className={`flex items-end gap-3 rounded-2xl border transition-colors duration-150 px-4 py-3 ${
          selectedDoc ? 'bg-white border-teal-200 focus-within:border-teal-500 focus-within:shadow-sm focus-within:shadow-teal-100' : 'bg-teal-50/50 border-teal-100'
        }`}>
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={e => {
              setInput(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 128) + 'px';
            }}
            onKeyDown={handleKeyDown}
            disabled={!selectedDoc || isLoading}
            placeholder={selectedDoc ? 'Ask a question about this document…' : 'Select a document to start'}
            aria-label="Question input"
            className="flex-1 resize-none bg-transparent text-sm text-teal-900 placeholder-teal-400 outline-none leading-relaxed disabled:cursor-not-allowed min-h-[24px] max-h-32"
            style={{ height: '24px' }}
          />
          <button
            onClick={handleSend}
            disabled={!canSend}
            aria-label="Send question"
            className={`shrink-0 w-9 h-9 rounded-xl flex items-center justify-center cursor-pointer transition-all duration-150 ${
              canSend
                ? 'bg-orange-500 hover:bg-orange-600 shadow-sm shadow-orange-200 text-white'
                : 'bg-teal-100 text-teal-300 cursor-not-allowed'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>
        <p className="text-xs text-teal-400 mt-2 text-center">
          {selectedDoc ? 'Press Enter to send · Shift+Enter for new line' : ''}
        </p>
      </div>
    </div>
  );
}
