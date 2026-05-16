import { ChevronRight } from 'lucide-react';
import type { Trend, AiLabels } from '../types';
import { resolveLabel } from '../lib/labels';

interface Props {
  trends: Trend[];
  aiLabels: AiLabels;
  onSelect: (topic: string) => void;
  selectedTopic: string | null;
}

const categoryStyles: Record<string, string> = {
  Conflict:
    'bg-rose-50 text-rose-700 border-rose-200 dark:bg-rose-500/10 dark:text-rose-300 dark:border-rose-500/30',
  Diplomacy:
    'bg-sky-50 text-sky-700 border-sky-200 dark:bg-sky-500/10 dark:text-sky-300 dark:border-sky-500/30',
  Geopolitics:
    'bg-indigo-50 text-indigo-700 border-indigo-200 dark:bg-indigo-500/10 dark:text-indigo-300 dark:border-indigo-500/30',
  'Media/Platforms':
    'bg-violet-50 text-violet-700 border-violet-200 dark:bg-violet-500/10 dark:text-violet-300 dark:border-violet-500/30',
  Society:
    'bg-emerald-50 text-emerald-700 border-emerald-200 dark:bg-emerald-500/10 dark:text-emerald-300 dark:border-emerald-500/30',
  'Domestic Politics':
    'bg-amber-50 text-amber-700 border-amber-200 dark:bg-amber-500/10 dark:text-amber-300 dark:border-amber-500/30',
  Other:
    'bg-slate-100 text-slate-600 border-slate-200 dark:bg-slate-700/40 dark:text-slate-300 dark:border-slate-600',
};

function categoryClass(cat?: string): string {
  if (!cat) return categoryStyles.Other;
  return categoryStyles[cat] || categoryStyles.Other;
}

export function TrendList({ trends, aiLabels, onSelect, selectedTopic }: Props) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800/60">
      <div className="p-5 md:p-6 border-b border-slate-200 dark:border-slate-700">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
          Top declining trends
        </h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Ranked by normalized September-to-December decline, weighted by topic significance.
          Click a row to inspect a trend.
        </p>
      </div>
      <ol className="divide-y divide-slate-200 dark:divide-slate-700">
        {trends.map((t, idx) => {
          const ai = aiLabels[t.topic];
          const label = resolveLabel(t.topic, aiLabels);
          const declinePct = Math.round(t.decline_percentage * 100);
          const isSelected = t.topic === selectedTopic;
          return (
            <li key={t.topic}>
              <button
                type="button"
                onClick={() => onSelect(t.topic)}
                className={`w-full text-left px-5 md:px-6 py-4 flex items-center gap-4 transition focus:outline-none focus:bg-slate-50 dark:focus:bg-slate-800 ${
                  isSelected
                    ? 'bg-indigo-50/60 dark:bg-indigo-500/10'
                    : 'hover:bg-slate-50 dark:hover:bg-slate-800/80'
                }`}
              >
                <div className="shrink-0 w-7 text-center text-sm font-mono text-slate-400 dark:text-slate-500">
                  {idx + 1}
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-medium text-slate-900 dark:text-slate-100 truncate">
                      {label}
                    </span>
                    {ai?.category && (
                      <span
                        className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded border ${categoryClass(ai.category)}`}
                      >
                        {ai.category}
                      </span>
                    )}
                  </div>
                  <div className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                    Sep {(t.sep_share * 100).toFixed(2)}% → Dec {(t.dec_share * 100).toFixed(2)}%
                    <span className="text-slate-400 dark:text-slate-500"> · keyword: {t.topic}</span>
                  </div>
                </div>
                <div className="shrink-0 w-28 hidden sm:block">
                  <div className="h-1.5 rounded-full bg-slate-100 dark:bg-slate-700 overflow-hidden">
                    <div
                      className="h-full bg-indigo-500 dark:bg-indigo-400"
                      style={{ width: `${Math.min(100, declinePct)}%` }}
                    />
                  </div>
                </div>
                <div className="shrink-0 w-16 text-right">
                  <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {declinePct}%
                  </div>
                  <div className="text-[10px] uppercase tracking-wide text-slate-400 dark:text-slate-500">
                    decline
                  </div>
                </div>
                <ChevronRight size={16} className="text-slate-300 dark:text-slate-500 shrink-0" />
              </button>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
