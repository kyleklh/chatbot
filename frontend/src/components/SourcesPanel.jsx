import { motion, AnimatePresence } from 'framer-motion';
import SourceCard from './SourceCard';

export default function SourcesPanel({ sources }) {
  return (
    <div className="flex flex-col h-full bg-stone-50">
      <div className="shrink-0 px-4 h-14 flex items-center bg-white border-b border-stone-200">
        <div className="flex items-center gap-2 w-full">
          <svg className="w-4 h-4 text-zinc-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
          </svg>
          <span className="text-[13px] font-semibold text-zinc-700 tracking-tight">Retrieved sources</span>
          {sources.length > 0 && (
            <span className="ml-auto text-[11px] font-medium text-zinc-400 font-mono">{sources.length}</span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        <AnimatePresence mode="sync">
          {sources.length === 0 ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex flex-col items-center justify-center h-full gap-3 text-center py-16"
            >
              <div className="w-12 h-12 rounded-xl bg-white border border-stone-200 flex items-center justify-center">
                <svg className="w-5 h-5 text-zinc-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
              </div>
              <p className="text-[13px] text-zinc-400 max-w-[200px]">Sources from your next answer will appear here</p>
            </motion.div>
          ) : (
            sources.map((source, i) => (
              <SourceCard key={i} source={source} index={i} />
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
