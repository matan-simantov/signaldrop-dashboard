import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import type { Methodology } from '../types';

interface Props {
  data: Methodology;
}

const SUMMARY =
  'We compare each topic’s share of monthly conversation in September and December, rather than raw counts, because overall posting volume changed significantly.';

const PIPELINE_STEPS = [
  'Extract keyword n-grams from translated post text.',
  'Calculate each topic’s monthly conversation share (mentions ÷ total posts in month).',
  'Rank topics by normalized September-to-December decline, weighted by topic significance.',
  'Filter out repeated alert templates and boilerplate UI text.',
  'Use AI only for human-readable labels and explanations — never for ranking.',
];

const THRESHOLD_LABELS: Record<string, { name: string; format: (v: number) => string }> = {
  min_sep_mentions: {
    name: 'Min Sep mentions',
    format: v => `${v.toLocaleString()} posts`,
  },
  min_sep_share: {
    name: 'Min Sep share',
    format: v => `${(v * 100).toFixed(2)}%`,
  },
  min_decline_percentage: {
    name: 'Min relative decline',
    format: v => `${Math.round(v * 100)}%`,
  },
};

function formatThreshold(key: string, val: number): { name: string; value: string } {
  const meta = THRESHOLD_LABELS[key];
  if (meta) return { name: meta.name, value: meta.format(val) };
  return { name: key.replace(/_/g, ' '), value: String(val) };
}

export function MethodologyCard({ data }: Props) {
  const [open, setOpen] = useState(false);

  return (
    <section className="rounded-xl border border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-800/60">
      <button
        onClick={() => setOpen(v => !v)}
        className="w-full flex items-center justify-between px-6 py-4 text-left"
        aria-expanded={open}
      >
        <div>
          <h2 className="text-base font-semibold text-slate-900 dark:text-slate-100">
            How trends are calculated
          </h2>
          <p className="mt-1 text-sm text-slate-600 dark:text-slate-400 max-w-3xl">
            {SUMMARY}
          </p>
        </div>
        <ChevronDown
          size={18}
          className={`shrink-0 text-slate-400 dark:text-slate-500 transition-transform ${
            open ? 'rotate-180' : ''
          }`}
        />
      </button>
      {open && (
        <div className="px-6 pb-6 pt-2 space-y-5 border-t border-slate-200 dark:border-slate-700">
          <div>
            <h3 className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
              Pipeline
            </h3>
            <ol className="space-y-2 text-sm text-slate-600 dark:text-slate-300 list-decimal list-inside marker:text-slate-400">
              {PIPELINE_STEPS.map(step => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
          {data.thresholds && (
            <div>
              <h3 className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
                Filtering thresholds
              </h3>
              <div className="grid grid-cols-3 gap-2">
                {Object.entries(data.thresholds).map(([key, val]) => {
                  const { name, value } = formatThreshold(key, val);
                  return (
                    <div
                      key={key}
                      className="rounded-lg p-2 text-center bg-slate-50 border border-slate-200 dark:bg-slate-900/40 dark:border-slate-700"
                    >
                      <div className="text-[10px] uppercase tracking-wide text-slate-500 dark:text-slate-400">
                        {name}
                      </div>
                      <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                        {value}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
          <div className="rounded-lg p-3 bg-slate-50 border border-slate-200 text-xs text-slate-600 dark:bg-slate-900/40 dark:border-slate-700 dark:text-slate-300 leading-relaxed">
            Topics whose normalized share <em>increased</em> from September to December are
            excluded from this ranking. This assignment focuses on{' '}
            <strong>declining</strong> conversation trends.
          </div>
          {data.limitations?.length > 0 && (
            <div>
              <h3 className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-2">
                Known limitations
              </h3>
              <ul className="text-sm text-slate-600 dark:text-slate-300 space-y-1 list-disc list-inside marker:text-slate-400">
                {data.limitations.map((lim, i) => (
                  <li key={i}>{lim}</li>
                ))}
              </ul>
            </div>
          )}
          <p className="text-xs text-slate-500 dark:text-slate-400 italic">
            Full technical details: see <code className="font-mono">README.md</code> and{' '}
            <code className="font-mono">ARCHITECTURE.md</code> in the repository.
          </p>
        </div>
      )}
    </section>
  );
}
