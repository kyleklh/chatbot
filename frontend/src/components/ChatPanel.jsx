import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { streamChat } from '../api';
import MarkdownBoundary from './MarkdownBoundary';

function CitationBadge({ num, source, onClick }) {
  const idx = parseInt(num, 10) - 1;
  const preview = source?.text ? source.text.slice(0, 200) + (source.text.length > 200 ? '…' : '') : null;
  const handleClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    onClick?.(idx);
  };
  return (
    <sup className="relative inline-block group/cite align-baseline mx-0.5">
      <button
        type="button"
        onClick={handleClick}
        aria-label={`Jump to source ${num}`}
        className="inline-flex items-center justify-center min-w-[20px] h-[20px] px-1 rounded-md bg-indigo-50 border border-indigo-200 text-indigo-700 font-mono text-[10px] font-medium cursor-pointer hover:bg-indigo-100 hover:border-indigo-300 hover:shadow-[0_0_10px_rgba(129,140,248,0.55)] transition-all duration-200"
      >
        {num}
      </button>
      {preview && (
        <span
          role="tooltip"
          className="pointer-events-none absolute left-1/2 bottom-full z-30 mb-1.5 w-72 -translate-x-1/2 rounded-lg border border-stone-200 bg-white px-3 py-2 text-left text-[12px] font-normal leading-relaxed text-zinc-700 shadow-lg opacity-0 group-hover/cite:opacity-100 transition-opacity duration-150"
        >
          <span className="block text-[10px] font-mono font-medium text-zinc-500 mb-1 truncate">
            {source.filename}{source.page != null || source.metadata?.page != null ? ` · p.${source.page ?? source.metadata?.page}` : ''}
          </span>
          {preview}
        </span>
      )}
    </sup>
  );
}

function renderWithCitations(children, sources, onCitationClick) {
  const process = (node) => {
    if (typeof node !== 'string') return node;
    const parts = node.split(/(\[(?:Source )?\d+\])/g);
    if (parts.length === 1) return node;
    return parts.map((part, i) => {
      const match = part.match(/\[(?:Source )?(\d+)\]/);
      if (!match) return part;
      const num = match[1];
      const idx = parseInt(num, 10) - 1;
      return <CitationBadge key={i} num={num} source={sources?.[idx]} onClick={onCitationClick} />;
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
          className="w-1.5 h-1.5 rounded-full bg-indigo-400"
          animate={{ y: [0, -4, 0], opacity: [0.5, 1, 0.5] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.12, ease: 'easeInOut' }}
        />
      ))}
    </div>
  );
}

function UserMessage({ text }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex justify-end">
      <div className="max-w-[75%] rounded-2xl rounded-tr-sm bg-indigo-500 px-4 py-2.5 shadow-sm shadow-indigo-500/20">
        <p className="text-[15px] leading-relaxed text-white">{text}</p>
      </div>
    </motion.div>
  );
}

function MessageActions({ onCopy, onRegenerate, onFeedback, copied, rating }) {
  const btn = "p-1.5 rounded-md text-zinc-400 hover:text-zinc-700 hover:bg-stone-100 cursor-pointer transition-colors duration-150";
  return (
    <div className="flex items-center gap-0.5 opacity-0 group-hover/msg:opacity-100 focus-within:opacity-100 transition-opacity duration-150">
      <button onClick={onCopy} aria-label={copied ? 'Copied' : 'Copy'} title={copied ? 'Copied' : 'Copy'} className={btn}>
        {copied ? (
          <svg className="w-3.5 h-3.5 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        ) : (
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
        )}
      </button>
      {onRegenerate && (
        <button onClick={onRegenerate} aria-label="Regenerate" title="Regenerate" className={btn}>
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        </button>
      )}
      <button onClick={() => onFeedback('up')} aria-label="Good response" title="Good response" className={`${btn} ${rating === 'up' ? 'text-green-600' : ''}`}>
        <svg className="w-3.5 h-3.5" fill={rating === 'up' ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
        </svg>
      </button>
      <button onClick={() => onFeedback('down')} aria-label="Bad response" title="Bad response" className={`${btn} ${rating === 'down' ? 'text-red-600' : ''}`}>
        <svg className="w-3.5 h-3.5" fill={rating === 'down' ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06L17 4m-7 10v5a2 2 0 002 2h.095c.5 0 .905-.405.905-.905 0-.714.211-1.412.608-2.006L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
        </svg>
      </button>
    </div>
  );
}

function SourcesPill({ count, isActive, onClick }) {
  if (!count) return null;
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label={isActive ? `Viewing ${count} sources` : `Show ${count} sources for this message`}
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium border cursor-pointer transition-all duration-150 ${
        isActive
          ? 'bg-indigo-50 border-indigo-300 text-indigo-700'
          : 'bg-white border-stone-200 text-zinc-500 hover:border-indigo-200 hover:text-indigo-600 hover:bg-indigo-50/50'
      }`}
    >
      <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
      </svg>
      <span>{count} source{count === 1 ? '' : 's'}</span>
      {isActive && <span className="text-indigo-500/70 font-mono text-[10px]">· viewing</span>}
    </button>
  );
}

// Strip a trailing unclosed `[...` from streaming text so remark-gfm doesn't
// crash on a half-arrived citation/link.
function sanitizeStreamingMarkdown(text) {
  if (!text) return text;
  return text.replace(/\[[^\]\n]*$/, '');
}

function AssistantMessage({ text, isStreaming, sources, isActive, onSelect, onViewSource, onRegenerate, canRegenerate }) {
  const showCursor = isStreaming && text !== '';
  const safeText = sanitizeStreamingMarkdown(text);
  const [copied, setCopied] = useState(false);
  const [rating, setRating] = useState(null);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      /* ignore */
    }
  };
  const handleFeedback = (value) => {
    const next = rating === value ? null : value;
    setRating(next);
    if (next) console.log('[feedback]', { rating: next, answer: text });
  };

  const handleCitationClick = (idx) => {
    if (idx == null || !sources?.[idx]) return;
    onSelect?.();
    onViewSource?.(sources[idx]);
  };

  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="group/msg flex gap-3 items-start">
      <div className="shrink-0 w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center mt-0.5 shadow-sm shadow-indigo-500/30">
        <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="2 5 14 14" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
        </svg>
      </div>
      <div className="flex-1 min-w-0">
      <div className={`rounded-2xl rounded-tl-sm bg-white border px-4 py-3 shadow-sm transition-colors duration-200 ${isActive ? 'border-indigo-300' : 'border-stone-200'}`}>
        {isStreaming && text === '' ? (
          <LoadingDots />
        ) : (
          <div className={showCursor ? 'streaming-cursor' : ''}>
            <MarkdownBoundary resetKey={safeText} fallbackText={safeText}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                p: ({ children }) => <p className="text-[15px] leading-relaxed text-zinc-800 mb-2 last:mb-0">{renderWithCitations(children, sources, handleCitationClick)}</p>,
                strong: ({ children }) => <strong className="font-semibold text-zinc-900">{renderWithCitations(children, sources, handleCitationClick)}</strong>,
                em: ({ children }) => <em className="italic text-zinc-700">{children}</em>,
                ul: ({ children }) => <ul className="list-disc list-inside space-y-1 my-2 text-[15px] text-zinc-800">{children}</ul>,
                ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 my-2 text-[15px] text-zinc-800">{children}</ol>,
                li: ({ children }) => <li className="text-[15px] leading-relaxed text-zinc-800">{renderWithCitations(children, sources, handleCitationClick)}</li>,
                code: ({ children }) => <code className="bg-stone-100 text-zinc-700 rounded px-1.5 py-0.5 text-[13px] font-mono">{children}</code>,
                h1: ({ children }) => <h1 className="text-base font-semibold text-zinc-900 mb-1.5 mt-3 tracking-tight">{children}</h1>,
                h2: ({ children }) => <h2 className="text-[15px] font-semibold text-zinc-900 mb-1 mt-2 tracking-tight">{children}</h2>,
                h3: ({ children }) => <h3 className="text-sm font-semibold text-zinc-900 mb-1 mt-2 tracking-tight">{children}</h3>,
                table: ({ children }) => (
                  <div className="overflow-x-auto my-3 rounded-lg border border-stone-200 -mx-1">
                    <table className="text-[13px] border-collapse w-full table-auto">{children}</table>
                  </div>
                ),
                thead: ({ children }) => <thead className="bg-stone-50">{children}</thead>,
                tbody: ({ children }) => <tbody>{children}</tbody>,
                tr: ({ children }) => <tr className="border-b border-stone-200 last:border-0 even:bg-stone-50/50 align-top">{children}</tr>,
                th: ({ children }) => <th className="text-left px-2.5 py-1.5 font-semibold text-zinc-700 text-[12px] leading-snug">{children}</th>,
                td: ({ children }) => <td className="px-2.5 py-1.5 text-zinc-800 whitespace-nowrap">{children}</td>,
              }}
            >
              {safeText}
            </ReactMarkdown>
            </MarkdownBoundary>
          </div>
        )}
      </div>
      {!isStreaming && text !== '' && (
        <div className="mt-1.5 flex items-center gap-1.5">
          <SourcesPill count={sources?.length || 0} isActive={isActive} onClick={onSelect} />
          <div className="ml-auto">
            <MessageActions
              onCopy={handleCopy}
              onRegenerate={canRegenerate ? onRegenerate : null}
              onFeedback={handleFeedback}
              copied={copied}
              rating={rating}
            />
          </div>
        </div>
      )}
      </div>
    </motion.div>
  );
}

function ErrorMessage({ text }) {
  return (
    <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} className="flex gap-3 items-start">
      <div className="shrink-0 w-7 h-7 rounded-lg bg-red-50 border border-red-200 flex items-center justify-center">
        <svg className="w-3.5 h-3.5 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      </div>
      <div className="rounded-2xl rounded-tl-sm bg-red-50 border border-red-200 px-4 py-3">
        <p className="text-[15px] text-red-700">{text}</p>
      </div>
    </motion.div>
  );
}

/* Animated gradient mesh background — used in the no-docs hero */
function GradientMesh() {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none -z-10">
      <div
        className="absolute w-[640px] h-[640px] rounded-full bg-indigo-300 blur-3xl opacity-40 drift-1"
        style={{ top: '-10%', left: '15%' }}
      />
      <div
        className="absolute w-[520px] h-[520px] rounded-full bg-violet-300 blur-3xl opacity-35 drift-2"
        style={{ bottom: '-10%', right: '10%' }}
      />
      <div
        className="absolute w-[420px] h-[420px] rounded-full bg-sky-200 blur-3xl opacity-30 drift-1"
        style={{ top: '40%', left: '50%', animationDelay: '-8s' }}
      />
    </div>
  );
}

function EmptyState({ hasDocuments, onSuggestionClick }) {
  const suggestions = [
    'What is this document about?',
    'Summarize the key points',
    'What are the main conclusions?',
    'List the important dates',
  ];

  if (!hasDocuments) {
    return (
      <div className="relative flex flex-col items-center justify-center h-full w-full">
        <GradientMesh />
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
          className="flex flex-col items-center gap-6 text-center px-8 max-w-xl"
        >
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-indigo-600 flex items-center justify-center shadow-xl shadow-indigo-500/40">
            <svg className="w-8 h-8 text-white" fill="none" viewBox="2 5 14 14" stroke="currentColor" strokeWidth={1.75}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
            </svg>
          </div>
          <div>
            <h2 className="text-3xl font-semibold text-zinc-900 tracking-tight">
              Ask anything across<br />your documents.
            </h2>
            <p className="text-[16px] text-zinc-600 mt-3 max-w-md mx-auto leading-relaxed">
              Upload PDFs. Query in plain English.<br />Get cited answers in seconds.
            </p>
          </div>
          <p className="text-[13px] text-zinc-500 mt-2 inline-flex items-center gap-2">
            <svg className="w-4 h-4 text-indigo-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
            </svg>
            Drop a PDF in the sidebar to begin
          </p>
        </motion.div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col items-center justify-center h-full gap-6 text-center px-8"
    >
      <div>
        <h2 className="text-2xl font-semibold text-zinc-900 tracking-tight">Ready when you are.</h2>
        <p className="text-[15px] text-zinc-500 mt-2 max-w-md">
          DocuRAG searches across your uploaded files and cites the source for every answer.
        </p>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-md">
        {suggestions.map(q => (
          <button
            key={q}
            onClick={() => onSuggestionClick(q)}
            className="rounded-xl border border-stone-200 bg-white px-3.5 py-2.5 text-left hover:border-indigo-300 hover:bg-indigo-50/50 hover:shadow-sm transition-all duration-200 cursor-pointer"
          >
            <p className="text-[13px] text-zinc-600">{q}</p>
          </button>
        ))}
      </div>
    </motion.div>
  );
}

const PLACEHOLDERS = [
  'Ask anything...',
  'What does this report say about Q3 revenue?',
  'Summarize the executive summary',
  'List the key findings',
  'Who are the main people mentioned?',
  'What were the financial highlights?',
];

export default function ChatPanel({ messages, onMessagesChange, onAnswer, hasDocuments, onViewSource, queryDocumentIds }) {
  const setMessages = onMessagesChange;
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [activeIndex, setActiveIndex] = useState(null);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const selectActive = (idx) => {
    setActiveIndex(idx);
    onAnswer?.(messages[idx]?.sources || []);
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  // Rotate placeholder while idle and empty
  useEffect(() => {
    if (input.length > 0 || isLoading) return;
    const id = setInterval(() => {
      setPlaceholderIndex(i => (i + 1) % PLACEHOLDERS.length);
    }, 3500);
    return () => clearInterval(id);
  }, [input, isLoading]);

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
      (srcs) => {
        setMessages(prev => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          updated[lastIdx] = { ...updated[lastIdx], sources: srcs };
          setActiveIndex(lastIdx);
          return updated;
        });
        onAnswer?.(srcs);
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
      { documentIds: queryDocumentIds },
    );
  };

  const handleRegenerate = (assistantIndex) => {
    if (isLoading) return;
    const userIndex = assistantIndex - 1;
    const userMsg = messages[userIndex];
    if (!userMsg || userMsg.type !== 'user') return;
    const trimmed = messages.slice(0, userIndex);
    const history = trimmed
      .filter(m => m.type === 'user' || m.type === 'assistant')
      .map(m => ({ role: m.type === 'user' ? 'user' : 'assistant', content: m.text }));
    setMessages([...trimmed, { type: 'user', text: userMsg.text }, { type: 'assistant', text: '' }]);
    setIsLoading(true);
    streamChat(
      userMsg.text,
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
      (srcs) => {
        setMessages(prev => {
          const updated = [...prev];
          const lastIdx = updated.length - 1;
          updated[lastIdx] = { ...updated[lastIdx], sources: srcs };
          setActiveIndex(lastIdx);
          return updated;
        });
        onAnswer?.(srcs);
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
      { documentIds: queryDocumentIds },
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
    <div className="flex flex-col flex-1 h-full overflow-hidden relative">
      {/* Messages — empty state fills full area; conversation gets max-w-3xl */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="h-full w-full flex items-center justify-center">
            <EmptyState hasDocuments={hasDocuments} onSuggestionClick={handleSend} />
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-6 py-6 space-y-4 flex flex-col">
            <AnimatePresence>
              {messages.map((msg, i) =>
                msg.type === 'user' ? (
                  <UserMessage key={i} text={msg.text} />
                ) : msg.type === 'assistant' ? (
                  <AssistantMessage
                    key={i}
                    text={msg.text}
                    isStreaming={isLoading && i === messages.length - 1}
                    sources={msg.sources}
                    isActive={i === activeIndex}
                    onSelect={() => selectActive(i)}
                    onViewSource={onViewSource}
                    canRegenerate={!isLoading && i === messages.length - 1 && i > 0 && messages[i - 1]?.type === 'user'}
                    onRegenerate={() => handleRegenerate(i)}
                  />
                ) : (
                  <ErrorMessage key={i} text={msg.text} />
                )
              )}
            </AnimatePresence>
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input — sticky bottom, centered */}
      {hasDocuments && (
        <div className="shrink-0 border-t border-stone-200 bg-white/80 backdrop-blur-md">
          <div className="max-w-3xl mx-auto px-6 py-4">
            <div className={`flex items-end gap-3 rounded-2xl border bg-white px-4 py-3 transition-all duration-200 ${
              isLoading
                ? 'border-stone-200'
                : 'border-stone-300 focus-within:border-indigo-400 focus-within:shadow-sm focus-within:shadow-indigo-500/10'
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
                placeholder={PLACEHOLDERS[placeholderIndex]}
                aria-label="Ask a question about your documents"
                className="flex-1 resize-none bg-transparent text-[15px] text-zinc-900 placeholder-zinc-400 outline-none leading-relaxed disabled:cursor-not-allowed min-h-[24px] max-h-28"
                style={{ height: '24px' }}
              />
              <button
                onClick={handleSend}
                disabled={!canSend}
                aria-label="Send"
                className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-200 cursor-pointer ${
                  canSend
                    ? 'bg-indigo-500 hover:bg-indigo-600 text-white shadow-sm shadow-indigo-500/30 hover:shadow-md hover:shadow-indigo-500/40'
                    : 'bg-stone-100 text-stone-300 cursor-not-allowed'
                }`}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
                </svg>
              </button>
            </div>
            <p className="text-[11px] text-zinc-400 mt-2 text-center font-mono">↵ to send · ⇧↵ for new line</p>
          </div>
        </div>
      )}
    </div>
  );
}
