import { useState, useEffect, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { pdfjs, Document, Page } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import { pdfUrl } from '../api';

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString();

const MIN_SCALE = 0.75;
const MAX_SCALE = 2.0;
const SCALE_STEP = 0.25;

function clamp(n, lo, hi) {
  return Math.max(lo, Math.min(hi, n));
}

function buildWindow(center, total) {
  if (!total || total < 1) return [];
  return [clamp(center, 1, total)];
}

export default function PdfViewer({ source, onClose }) {
  const [numPages, setNumPages] = useState(null);
  const [center, setCenter] = useState(source?.page ?? 1);
  const [scale, setScale] = useState(1.0);
  const [loadError, setLoadError] = useState(null);
  const previouslyFocused = useRef(null);
  const dialogRef = useRef(null);
  const scrollRef = useRef(null);

  const url = useMemo(
    () => (source?.document_id ? pdfUrl(source.document_id) : null),
    [source?.document_id],
  );

  // Reset when source changes
  useEffect(() => {
    setNumPages(null);
    setLoadError(null);
    setCenter(source?.page ?? 1);
    setScale(1.0);
  }, [source?.document_id, source?.page]);

  // Esc to close + focus management
  useEffect(() => {
    if (!source) return;
    previouslyFocused.current = document.activeElement;
    const handleKey = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    document.addEventListener('keydown', handleKey);
    dialogRef.current?.focus();
    return () => {
      document.removeEventListener('keydown', handleKey);
      previouslyFocused.current?.focus?.();
    };
  }, [source, onClose]);

  // Scroll to top of pages container when window changes
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: 0 });
  }, [center]);

  if (!source) return null;

  const visiblePages = buildWindow(center, numPages);
  const canPrev = numPages != null && center > 1;
  const canNext = numPages != null && center < numPages;
  const canZoomOut = scale > MIN_SCALE + 0.001;
  const canZoomIn = scale < MAX_SCALE - 0.001;

  return (
    <AnimatePresence>
      <motion.div
        key="pdf-backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.15 }}
        onClick={onClose}
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm p-6"
      >
        <motion.div
          ref={dialogRef}
          tabIndex={-1}
          role="dialog"
          aria-modal="true"
          aria-label={`PDF viewer: ${source.filename}, page ${source.page}`}
          initial={{ opacity: 0, scale: 0.96, y: 8 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 8 }}
          transition={{ duration: 0.18, ease: 'easeOut' }}
          onClick={(e) => e.stopPropagation()}
          className="relative flex flex-col w-full max-w-4xl h-[90vh] rounded-2xl bg-white shadow-2xl overflow-hidden outline-none"
        >
          {/* Header */}
          <div className="shrink-0 flex items-center gap-3 px-5 h-14 border-b border-stone-200">
            <svg className="w-4 h-4 text-zinc-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            <span className="text-[14px] font-semibold text-zinc-800 truncate" title={source.filename}>
              {source.filename}
            </span>
            <span className="text-[12px] font-mono text-zinc-500 shrink-0">
              {numPages ? `Page ${center} of ${numPages}` : `Page ${source.page}`}
            </span>
            <div className="ml-auto flex items-center gap-1">
              <button
                onClick={() => setScale(s => clamp(s - SCALE_STEP, MIN_SCALE, MAX_SCALE))}
                disabled={!canZoomOut}
                aria-label="Zoom out"
                title="Zoom out"
                className="w-8 h-8 rounded-md text-zinc-500 hover:text-zinc-800 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center transition-colors duration-150"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 12h-15" />
                </svg>
              </button>
              <span className="text-[11px] font-mono text-zinc-500 w-10 text-center tabular-nums">{Math.round(scale * 100)}%</span>
              <button
                onClick={() => setScale(s => clamp(s + SCALE_STEP, MIN_SCALE, MAX_SCALE))}
                disabled={!canZoomIn}
                aria-label="Zoom in"
                title="Zoom in"
                className="w-8 h-8 rounded-md text-zinc-500 hover:text-zinc-800 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center transition-colors duration-150"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
              </button>
              <div className="w-px h-5 bg-stone-200 mx-1" />
              <button
                onClick={() => setCenter(c => clamp(c - 1, 1, numPages ?? 1))}
                disabled={!canPrev}
                aria-label="Previous page"
                title="Previous page"
                className="w-8 h-8 rounded-md text-zinc-500 hover:text-zinc-800 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center transition-colors duration-150"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5L8.25 12l7.5-7.5" />
                </svg>
              </button>
              <button
                onClick={() => setCenter(c => clamp(c + 1, 1, numPages ?? 1))}
                disabled={!canNext}
                aria-label="Next page"
                title="Next page"
                className="w-8 h-8 rounded-md text-zinc-500 hover:text-zinc-800 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed cursor-pointer flex items-center justify-center transition-colors duration-150"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              </button>
              <div className="w-px h-5 bg-stone-200 mx-1" />
              <button
                onClick={onClose}
                aria-label="Close"
                title="Close (Esc)"
                className="w-8 h-8 rounded-md text-zinc-500 hover:text-zinc-800 hover:bg-stone-100 cursor-pointer flex items-center justify-center transition-colors duration-150"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Body */}
          <div ref={scrollRef} className="flex-1 overflow-auto bg-stone-100 px-4 py-4">
            {loadError ? (
              <div className="h-full flex flex-col items-center justify-center text-center gap-2">
                <p className="text-[14px] text-zinc-700">This document is no longer available.</p>
                <p className="text-[12px] text-zinc-500">{loadError}</p>
              </div>
            ) : (
              <Document
                file={url}
                onLoadSuccess={({ numPages: n }) => {
                  setNumPages(n);
                  setCenter(c => clamp(c, 1, n));
                }}
                onLoadError={(err) => setLoadError(err?.message || 'Failed to load PDF.')}
                loading={
                  <div className="h-full flex items-center justify-center text-[13px] text-zinc-500">
                    Loading PDF…
                  </div>
                }
              >
                <div className="flex flex-col items-center gap-4">
                  {visiblePages.map(p => (
                    <div key={p} className="relative">
                      <span className="absolute -left-2 top-2 z-10 inline-flex items-center rounded-md bg-white/90 backdrop-blur-sm border border-stone-200 px-1.5 py-0.5 text-[10px] font-mono text-zinc-600 shadow-sm">
                        p.{p}
                      </span>
                      <Page
                        pageNumber={p}
                        scale={scale}
                        renderAnnotationLayer={false}
                        renderTextLayer={false}
                        className="shadow-md bg-white"
                      />
                    </div>
                  ))}
                </div>
              </Document>
            )}
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
