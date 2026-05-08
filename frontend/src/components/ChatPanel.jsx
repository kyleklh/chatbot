import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { streamChat } from '../api';

function CitationBadge({ num }) {
  return (
    <sup className="text-cyan-600 font-semibold text-[10px] mx-0.5">[{num}]</sup>
  );
}

function renderWithCitations(children) {
  const process = (node) => {
    if (typeof node !== 'string') return node;
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

function LoadingDots() {
  return (
    <div className="flex items-center gap-1 px-1 py-1">
      {[0, 1, 2].map(i => (
        <motion.span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-slate-400"
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 0.5, repeat: Infinity, delay: i * 0.12, ease: 'easeInOut' }}
        />
      ))}
    </div>
  );
}

function UserMessage({ text }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
      <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-cyan-600 px-4 py-2.5">
        <p className="text-sm leading-relaxed text-white">{text}</p>
      </div>
    </motion.div>
  );
}

function AssistantMessage({ text, isStreaming }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-2.5 items-start">
      <div className="shrink-0 w-7 h-7 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center mt-0.5">
        <svg className="w-3.5 h-3.5 text-slate-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
        </svg>
      </div>
      <div className="max-w-full rounded-2xl rounded-tl-sm bg-white border border-slate-200 px-4 py-3 shadow-sm overflow-x-auto">
        {isStreaming && text === '' ? (
          <LoadingDots />
        ) : (
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              p: ({ children }) => <p className="text-sm leading-relaxed text-slate-800 mb-2 last:mb-0">{renderWithCitations(children)}</p>,
              strong: ({ children }) => <strong className="font-semibold text-slate-900">{renderWithCitations(children)}</strong>,
              em: ({ children }) => <em className="italic text-slate-700">{children}</em>,
              ul: ({ children }) => <ul className="list-disc list-inside space-y-1 my-2 text-sm text-slate-800">{children}</ul>,
              ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 my-2 text-sm text-slate-800">{children}</ol>,
              li: ({ children }) => <li className="text-sm leading-relaxed text-slate-800">{renderWithCitations(children)}</li>,
              code: ({ children }) => <code className="bg-slate-100 text-slate-700 rounded px-1 py-0.5 text-xs font-mono">{children}</code>,
              h1: ({ children }) => <h1 className="text-base font-bold text-slate-900 mb-1 mt-2">{children}</h1>,
              h2: ({ children }) => <h2 className="text-sm font-bold text-slate-900 mb-1 mt-2">{children}</h2>,
              h3: ({ children }) => <h3 className="text-sm font-semibold text-slate-900 mb-1 mt-2">{children}</h3>,
              table: ({ children }) => (
                <div className="overflow-x-auto my-3">
                  <table className="text-xs border-collapse w-full">{children}</table>
                </div>
              ),
              thead: ({ children }) => <thead className="bg-slate-100">{children}</thead>,
              tbody: ({ children }) => <tbody>{children}</tbody>,
              tr: ({ children }) => <tr className="border-b border-slate-200 even:bg-slate-50">{children}</tr>,
              th: ({ children }) => <th className="text-left px-2 py-1.5 font-semibold text-slate-700 border border-slate-200 whitespace-nowrap">{children}</th>,
              td: ({ children }) => <td className="px-2 py-1.5 text-slate-800 border border-slate-200 whitespace-nowrap">{children}</td>,
            }}
          >
            {text}
          </ReactMarkdown>
        )}
      </div>
    </motion.div>
  );
}

function ErrorMessage({ text }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-2.5 items-start">
      <div className="shrink-0 w-7 h-7 rounded-full bg-red-50 border border-red-200 flex items-center justify-center">
        <svg className="w-3.5 h-3.5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <div className="rounded-2xl rounded-tl-sm bg-red-50 border border-red-200 px-4 py-3">
        <p className="text-sm text-red-700">{text}</p>
      </div>
    </motion.div>
  );
}

function EmptyState({ hasDocuments, onUploadClick, onSuggestionClick }) {
  const suggestions = [
    'What is this document about?',
    'Summarize the key points',
    'What are the main conclusions?',
    'List the important dates',
  ];

  if (!hasDocuments) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex flex-col items-center justify-center h-full gap-4 text-center px-8"
      >
        <div className="w-14 h-14 rounded-2xl bg-cyan-50 border border-cyan-200 flex items-center justify-center">
          <svg className="w-7 h-7 text-cyan-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
        </div>
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Upload your documents to get started</h2>
          <p className="text-sm text-slate-500 mt-1 max-w-xs">
            Add your PDFs and DocuRAG will let you ask questions across all of them.
          </p>
        </div>
        <button
          onClick={onUploadClick}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-cyan-600 text-white text-sm font-medium hover:bg-cyan-700 transition-colors duration-150 cursor-pointer"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
          </svg>
          Upload PDFs
        </button>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center h-full gap-5 text-center px-8"
    >
      <div>
        <h2 className="text-lg font-semibold text-slate-800">Ask anything about your documents</h2>
        <p className="text-sm text-slate-500 mt-1 max-w-sm">
          DocuRAG searches across all your uploaded files and cites the source for every answer.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-sm">
        {suggestions.map(q => (
          <button
            key={q}
            onClick={() => onSuggestionClick(q)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-left hover:border-cyan-400 hover:bg-cyan-50 transition-colors duration-150 cursor-pointer"
          >
            <p className="text-xs text-slate-500">{q}</p>
          </button>
        ))}
      </div>
    </motion.div>
  );
}

export default function ChatPanel({ onAnswer, hasDocuments, onUploadClick }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = (overrideQuestion) => {
    const question = (typeof overrideQuestion === 'string' ? overrideQuestion : input).trim();
    if (!question || isLoading) return;

    const history = messages
      .filter(m => m.type === 'user' || m.type === 'assistant')
      .map(m => ({ role: m.type === 'user' ? 'user' : 'assistant', content: m.text }));

    setMessages(prev => [...prev, { type: 'user', text: question }, { type: 'assistant', text: '' }]);
    setInput('');
    setIsLoading(true);
    textareaRef.current?.focus();

    streamChat(
      question,
      null,
      history,
      (token) => {
        setMessages(prev => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = { ...last, text: last.text + token };
          return updated;
        });
      },
      (sources) => {
        onAnswer?.(sources);
        setIsLoading(false);
      },
      (err) => {
        setMessages(prev => {
          const updated = [...prev];
          updated[updated.length - 1] = { type: 'error', text: err.message };
          return updated;
        });
        onAnswer?.([]);
        setIsLoading(false);
      },
    );
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const canSend = input.trim().length > 0 && !isLoading;

  return (
    <div className="flex flex-col flex-1 h-full overflow-hidden bg-white">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
        {messages.length === 0 ? (
          <EmptyState hasDocuments={hasDocuments} onUploadClick={onUploadClick} onSuggestionClick={handleSend} />
        ) : (
          <>
            <AnimatePresence>
              {messages.map((msg, i) =>
                msg.type === 'user' ? (
                  <UserMessage key={i} text={msg.text} />
                ) : msg.type === 'assistant' ? (
                  <AssistantMessage key={i} text={msg.text} isStreaming={isLoading && i === messages.length - 1} />
                ) : (
                  <ErrorMessage key={i} text={msg.text} />
                )
              )}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* Input */}
      {hasDocuments && <div className="shrink-0 border-t border-slate-200 bg-white px-5 py-4">
        <div className={`flex items-end gap-3 rounded-xl border px-4 py-3 transition-colors duration-150 ${
          isLoading ? 'bg-slate-50 border-slate-200' : 'bg-white border-slate-300 focus-within:border-cyan-500'
        }`}>
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={e => {
              setInput(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            }}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="Ask your docs..."
            aria-label="Ask a question about your documents"
            className="flex-1 resize-none bg-transparent text-sm text-slate-800 placeholder-slate-400 outline-none leading-relaxed disabled:cursor-not-allowed min-h-[22px] max-h-28"
            style={{ height: '22px' }}
          />
          <button
            onClick={handleSend}
            disabled={!canSend}
            aria-label="Send"
            className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-150 cursor-pointer ${
              canSend ? 'bg-cyan-600 hover:bg-cyan-700 text-white' : 'bg-slate-100 text-slate-300 cursor-not-allowed'
            }`}
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>
        <p className="text-xs text-slate-400 mt-2 text-center">Enter to send · Shift+Enter for new line</p>
      </div>}
    </div>
  );
}
