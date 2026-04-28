import { useState } from 'react';
import { motion } from 'framer-motion';

export default function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false);
  const page = source.page ?? source.metadata?.page;
  const isLong = source.text.length > 200;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="rounded-xl border border-slate-200 bg-white overflow-hidden shadow-sm"
    >
      <div className="flex items-center gap-2 px-3 py-2 border-b border-slate-100 bg-slate-50">
        <span className="text-xs font-semibold text-slate-600">Source {index + 1}</span>

        <span className="text-xs text-slate-400 truncate max-w-[120px]" title={source.filename}>
          {source.filename}
        </span>

        {page != null && (
          <span className="inline-flex items-center rounded-md bg-slate-100 border border-slate-200 px-1.5 py-0.5 text-xs font-medium text-slate-600">
            p.{page}
          </span>
        )}

      </div>

      <div className="px-3 py-2.5">
        <p className="text-xs leading-relaxed text-slate-700">
          {expanded || !isLong ? source.text : source.text.slice(0, 200) + '…'}
        </p>
        {isLong && (
          <button
            onClick={() => setExpanded(v => !v)}
            className="mt-1.5 text-xs font-medium text-cyan-600 hover:text-cyan-800 cursor-pointer transition-colors duration-150"
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>
    </motion.div>
  );
}
