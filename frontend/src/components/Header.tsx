import { Moon, Sun } from 'lucide-react';
import type { Overview } from '../types';
import type { Theme } from '../hooks/useTheme';

interface Props {
  overview: Overview | null;
  theme: Theme;
  onToggleTheme: () => void;
}

function formatRange(start: string, end: string): string {
  // Expected ISO-ish dates: keep it simple, fall back to default chip text
  try {
    const s = new Date(start);
    const e = new Date(end);
    const fmt = (d: Date) =>
      d.toLocaleDateString('en-US', { month: 'short', year: 'numeric' });
    return `${fmt(s)} – ${fmt(e)}`;
  } catch {
    return 'Sep – Dec 2025';
  }
}

export function Header({ overview, theme, onToggleTheme }: Props) {
  const totalPosts = overview ? overview.total_posts.toLocaleString() : '—';
  const channels = overview ? overview.channels.toLocaleString() : '—';
  const range = overview
    ? formatRange(overview.date_range.start, overview.date_range.end)
    : 'Sep – Dec 2025';

  const chips = [
    'Telegram',
    range,
    `${totalPosts} posts`,
    `${channels} channels`,
  ];

  return (
    <header className="space-y-4">
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
            Signal<span className="text-indigo-600 dark:text-indigo-400">Drop</span>
          </h1>
          <p className="text-slate-600 dark:text-slate-300 text-base max-w-3xl leading-relaxed">
            SignalDrop analyzes 694K public Telegram posts and highlights topics whose
            share of conversation declined from September to December 2025.
          </p>
        </div>
        <button
          onClick={onToggleTheme}
          aria-label={theme === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}
          className="shrink-0 inline-flex items-center justify-center h-9 w-9 rounded-lg border border-slate-200 bg-white text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700 dark:hover:text-slate-100"
        >
          {theme === 'light' ? <Moon size={16} /> : <Sun size={16} />}
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {chips.map(c => (
          <span
            key={c}
            className="text-xs px-2.5 py-1 rounded-full bg-slate-100 text-slate-700 border border-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:border-slate-700"
          >
            {c}
          </span>
        ))}
      </div>
    </header>
  );
}
