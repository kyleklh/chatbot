import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

function relevanceInfo(distance) {
  if (distance == null) return null;
  // L2 distance with normalized embeddings: cos_sim = 1 - d²/2
  const sim = Math.max(0, Math.min(1, 1 - (distance * distance) / 2));
  const pct = Math.round(sim * 100);
  if (sim >= 0.75) return { label: `${pct}% match`, color: 'text-teal-700 bg-teal-100' };
  if (sim >= 0.55) return { label: `${pct}% match`, color: 'text-amber-700 bg-amber-100' };
  return { label: `${pct}% match`, color: 'text-slate-500 bg-slate-100' };
}

export default function SourceCard({ source, index }) {
  const [expanded, setExpanded] = useState(false);

  const page = source.page ?? source.metadata?.page;
  const rel = relevanceInfo(source.distance);
  const isLong = source.text.length > 200;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06 }}
      className="rounded-xl border border-teal-100 bg-white/70 backdrop-blur-sm overflow-hidden"
    >
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-teal-50 bg-teal-50/50">
        <span className="text-xs font-semibold text-teal-700">Source {index + 1}</span>

        {page != null && (
          <span className="inline-flex items-center gap-1 rounded-full bg-teal-100 px-2 py-0.5 text-xs font-medium text-teal-700">
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
            p.{page}
          </span>
        )}

        {rel && (
          <span className={`ml-auto text-xs font-medium px-2 py-0.5 rounded-full ${rel.color}`}>
            {rel.label}
          </span>
        )}
      </div>

      <div className="px-4 py-3">
        <AnimatePresence initial={false}>
          <motion.p
            key={expanded ? 'expanded' : 'collapsed'}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="text-sm leading-relaxed text-teal-900"
          >
            {expanded || !isLong ? source.text : source.text.slice(0, 200) + '…'}
          </motion.p>
        </AnimatePresence>

        {isLong && (
          <button
            onClick={() => setExpanded(v => !v)}
            className="mt-2 text-xs font-medium text-teal-600 hover:text-teal-800 cursor-pointer transition-colors duration-150"
          >
            {expanded ? 'Show less' : 'Show more'}
          </button>
        )}
      </div>
    </motion.div>
  );
}
