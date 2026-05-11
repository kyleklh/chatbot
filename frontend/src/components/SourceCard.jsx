import { useState } from 'react';
import { motion } from 'framer-motion';

export default function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false);
  const page = source.page ?? source.metadata?.page;
  const isLong = source.text.length > 200;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay: index * 0.07, duration: 0.3, ease: 'easeOut' }}
      className="rounded-xl border border-stone-200 bg-white overflow-hidden shadow-sm hover:border-indigo-200 hover:shadow-md transition-all duration-200"
    >
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-stone-100">
        <span className="inline-flex items-center justify-center w-5 h-5 rounded-md bg-indigo-50 border border-indigo-200 text-indigo-700 font-mono text-[11px] font-medium">
          {index + 1}
        </span>
        <span className="text-[12px] text-zinc-500 truncate flex-1" title={source.filename}>
          {source.filename}
        </span>
        {page != null && (
          <span className="inline-flex items-center rounded-md bg-stone-100 px-1.5 py-0.5 text-[11px] font-medium text-zinc-600 font-mono">
            p.{page}
          </span>
        )}
      </div>

      <div className="px-3 py-2">
        <p className="text-[13px] leading-relaxed text-zinc-700">
          {expanded || !isLong ? source.text : source.text.slice(0, 200) + '…'}
        </p>
        {isLong && (
          <button
            onClick={() => setExpanded(v => !v)}
            className="mt-1 text-[12px] font-medium text-indigo-600 hover:text-indigo-700 cursor-pointer transition-colors duration-150"
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>
    </motion.div>
  );
}
