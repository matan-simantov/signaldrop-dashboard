import { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import type { Methodology } from '../types';

interface Props {
  data: Methodology;
}

const SUMMARY =
  'We rank topic signals by their normalized September-to-December decline in share of unique deduplicated cleaned-text posts, not by raw counts. Cross-posted copies of the same message collapse into one canonical post so a single forwarded text does not look like many independent occurrences.';

const PIPELINE_STEPS = [
  'Load every observed Telegram post into an in-memory database.',
  'Clean each post (lowercase, strip URLs, remove punctuation, collapse whitespace) and hash the cleaned text with SHA-1.',
  'Mark canonical posts: keep one row per cleaned-text hash (earliest published_at wins). All downstream steps use canonical posts only.',
  'Filter Home Front Command alert templates and UI / social-footer boilerplate (whatsapp, instagram, tiktok, …) before n-gram extraction.',
  'Extract unigrams + bigrams per canonical post; deduplicate n-grams within each post.',
  'Compute monthly_share = canonical posts mentioning the topic ÷ total canonical posts in month.',
  'Rank by normalized Sep→Dec decline, weighted by September topic share.',
  'Consolidate duplicate lexical signals only when reciprocal post-level overlap is strong, using the union of canonical post IDs.',
  'Prefer displayable topic-like groups in the main list while keeping generic signals in artifacts for auditability.',
  'Use AI only for readable labels and summaries — never for ranking, grouping, counts, shares, or decline metrics.',
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
              Metrics &amp; dimensions
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm text-slate-600 dark:text-slate-300">
              <div>
                <div className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-1">
                  Metrics
                </div>
                <ul className="space-y-1 list-disc list-inside marker:text-slate-400">
                  <li>Observed Telegram posts</li>
                  <li>Canonical (unique deduplicated cleaned-text) posts</li>
                  <li>Normalized monthly share (canonical mentions ÷ canonical posts in month)</li>
                  <li>September → December decline (absolute and percentage)</li>
                  <li>Ranking score = decline × September share</li>
                </ul>
              </div>
              <div>
                <div className="text-[11px] uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-1">
                  Dimensions
                </div>
                <ul className="space-y-1 list-disc list-inside marker:text-slate-400">
                  <li>Month (Sep / Oct / Nov / Dec 2025)</li>
                  <li>Topic / consolidated topic group</li>
                  <li>First observed channel (after dedup)</li>
                </ul>
              </div>
            </div>
          </div>
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
            <strong>declining</strong> topic signals. Consolidated groups use the union of
            canonical post IDs, so duplicate member signals never double count the same post.
            Channel attribution after dedup reflects the <em>first observed channel</em> for a
            cleaned-text hash, which is not necessarily the original source.
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
