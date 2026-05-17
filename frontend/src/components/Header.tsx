import { Moon, Sun } from 'lucide-react';
import type { Theme } from '../hooks/useTheme';

type Variant = 'home' | 'telegram';

interface Props {
  theme: Theme;
  onToggleTheme: () => void;
  variant?: Variant;
}

const COPY: Record<Variant, string> = {
  home:
    'Analyze public text datasets and detect topic signals whose normalized share of observed posts is declining over time.',
  telegram:
    'Observed public Telegram posts, September–December 2025. Topic signals ranked by normalized decline in share of unique deduplicated cleaned-text posts.',
};

export function Header({ theme, onToggleTheme, variant = 'home' }: Props) {
  return (
    <header>
      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-3xl md:text-4xl font-semibold tracking-tight text-slate-900 dark:text-slate-50">
            Signal<span className="text-indigo-600 dark:text-indigo-400">Drop</span>
          </h1>
          <p className="text-slate-600 dark:text-slate-300 text-base max-w-3xl leading-relaxed">
            {COPY[variant]}
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
    </header>
  );
}
