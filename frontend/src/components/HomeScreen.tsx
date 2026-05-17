import { Database, Lock, ArrowRight } from 'lucide-react';

interface Props {
  onOpenTelegram: () => void;
}

export function HomeScreen({ onOpenTelegram }: Props) {
  return (
    <section className="space-y-8">
      <div className="space-y-3 max-w-3xl">
        <h2 className="text-2xl font-semibold text-slate-900 dark:text-slate-100">
          Datasets
        </h2>
        <p className="text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
          Select a public conversation dataset to open its analysis workspace. Each workspace
          detects topic signals whose normalized share of observed posts is declining over time,
          using deterministic metrics over deduplicated cleaned-text posts. AI is used only for
          readable labels and summaries — never for ranking, counts, or grouping.
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <ActiveDatasetCard onOpen={onOpenTelegram} />
        <DisabledDatasetCard
          title="Facebook Public Posts"
          subtitle="Coming soon"
        />
        <DisabledDatasetCard
          title="Other Public Text Sources"
          subtitle="Supported through normalized source loaders"
        />
      </div>
    </section>
  );
}

function ActiveDatasetCard({ onOpen }: { onOpen: () => void }) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="group text-left rounded-xl border border-indigo-200 bg-white p-5 shadow-sm transition hover:border-indigo-300 hover:shadow-md focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:border-indigo-500/30 dark:bg-slate-800/70 dark:hover:border-indigo-400/60"
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-indigo-50 text-indigo-600 dark:bg-indigo-500/10 dark:text-indigo-300">
          <Database size={18} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold text-slate-900 dark:text-slate-100">
            Public Telegram Channels Dataset
          </div>
          <p className="mt-1.5 text-sm text-slate-600 dark:text-slate-300 leading-relaxed">
            Observed public Telegram posts analyzed for declining topic signals across deduplicated
            cleaned-text posts between September and December 2025.
          </p>
          <div className="mt-3 text-xs text-slate-500 dark:text-slate-400">
            693,989 observed · 593,094 unique cleaned-text · 366 channels · Sep–Dec 2025
          </div>
          <div className="mt-4 inline-flex items-center gap-1.5 text-xs font-medium text-indigo-600 transition group-hover:gap-2 dark:text-indigo-300">
            Open Telegram analysis
            <ArrowRight size={13} />
          </div>
        </div>
      </div>
    </button>
  );
}

function DisabledDatasetCard({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div
      aria-disabled="true"
      className="rounded-xl border border-dashed border-slate-200 bg-slate-50/60 p-5 text-slate-500 cursor-not-allowed select-none dark:border-slate-700 dark:bg-slate-900/30 dark:text-slate-400"
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-white text-slate-400 dark:bg-slate-800 dark:text-slate-500">
          <Lock size={16} />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-medium text-slate-600 dark:text-slate-300">
            {title}
          </div>
          <p className="mt-1.5 text-xs leading-relaxed">{subtitle}</p>
          <div className="mt-4 inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">
            Unavailable
          </div>
        </div>
      </div>
    </div>
  );
}
