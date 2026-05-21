import { ChevronRight } from 'lucide-react';
import type { Trend, AiLabels } from '../types';
import { resolveTrendLabel } from '../lib/labels';
import { InfoTooltip } from './InfoTooltip';

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
        <div className="flex items-center gap-1.5">
          <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
            Top declining topic signals
          </h2>
          <InfoTooltip
            term="ranking score"
            text="Ranked by decline weighted by September topic share. Tiny topics that vanish entirely don't outrank large topics with real shifts."
          />
        </div>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">
          Sorted by deterministic ranking score (decline × September share). Select any topic to
          inspect its monthly share, channel-level drops, and example September posts below.
        </p>
      </div>
      <ol className="divide-y divide-slate-200 dark:divide-slate-700">
        {trends.map((t, idx) => {
          const ai = aiLabels[t.topic] || (t.representative_topic ? aiLabels[t.representative_topic] : undefined);
          const label = resolveTrendLabel(t, aiLabels);
          const signal = t.representative_topic || t.topic;
          const declinePct = Math.round(t.decline_percentage * 100);
          const isSelected = t.topic === selectedTopic;
          return (
            <li key={t.topic} className="relative">
              {isSelected && (
                <span
                  aria-hidden
                  className="absolute inset-y-0 left-0 w-1 bg-indigo-500 dark:bg-indigo-400"
                />
              )}
              <button
                type="button"
                onClick={() => onSelect(t.topic)}
                aria-pressed={isSelected}
                className={`w-full text-left px-5 md:px-6 py-4 flex items-center gap-4 transition focus:outline-none focus:bg-slate-50 dark:focus:bg-slate-800 ${
                  isSelected
                    ? 'bg-indigo-50 dark:bg-indigo-500/15'
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
                  <div className="mt-1 text-xs text-slate-500 dark:text-slate-400 truncate">
                    signal: {signal}
                  </div>
                </div>
                <div className="shrink-0 w-24 text-right hidden sm:block">
                  <div className="text-xs tabular-nums text-slate-700 dark:text-slate-200 leading-tight">
                    Sep {(t.sep_share * 100).toFixed(2)}%
                  </div>
                  <div className="text-xs tabular-nums text-slate-500 dark:text-slate-400 leading-tight">
                    Dec {(t.dec_share * 100).toFixed(2)}%
                  </div>
                  <div className="mt-0.5 text-[10px] uppercase tracking-wide text-slate-400 dark:text-slate-500 inline-flex items-center gap-0.5">
                    share
                    {idx === 0 && (
                      <InfoTooltip
                        term="monthly share"
                        text="Topic mentions in this month ÷ total canonical (deduplicated) posts in this month."
                        size={11}
                      />
                    )}
                  </div>
                </div>
                <div className="shrink-0 w-20 text-right hidden sm:block">
                  <div className="text-lg font-bold tabular-nums text-indigo-600 dark:text-indigo-300 leading-none">
                    {Math.round(t.ranking_score * 10000).toLocaleString()}
                  </div>
                  <div className="mt-1 text-[10px] uppercase tracking-wide font-medium text-indigo-500/80 dark:text-indigo-300/80 inline-flex items-center gap-0.5">
                    score
                    {idx === 0 && (
                      <InfoTooltip
                        term="ranking score"
                        text="absolute_delta × decline_percentage, scaled ×10,000. Normalized Sep→Dec decline weighted by September topic share — table is sorted by this value."
                        size={11}
                      />
                    )}
                  </div>
                </div>
                <div className="shrink-0 w-16 text-right">
                  <div className="text-sm font-semibold tabular-nums text-slate-900 dark:text-slate-100">
                    {declinePct}%
                  </div>
                  <div className="text-[10px] uppercase tracking-wide text-slate-400 dark:text-slate-500 inline-flex items-center gap-0.5">
                    decline
                    {idx === 0 && (
                      <InfoTooltip
                        term="decline percentage"
                        text="(Sep share − Dec share) ÷ Sep share. Share of September attention lost by December."
                        size={11}
                      />
                    )}
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
