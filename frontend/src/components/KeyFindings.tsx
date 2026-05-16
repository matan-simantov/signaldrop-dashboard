import type { Insight } from '../lib/insights';

interface Props {
  findings: Insight[];
}

export function KeyFindings({ findings }: Props) {
  if (findings.length === 0) return null;

  return (
    <section>
      <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 mb-3">
        Key findings
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {findings.map(f => (
          <div
            key={f.title}
            className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800/60"
          >
            <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
              {f.title}
            </div>
            <div className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-50">
              {f.value}
            </div>
            <p className="mt-2 text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
              {f.detail}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
