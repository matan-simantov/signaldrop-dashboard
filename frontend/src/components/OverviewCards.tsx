import { TrendingDown, Radio, Calendar, Hash } from 'lucide-react';
import type { Overview } from '../types';

interface Props {
  data: Overview;
}

export function OverviewCards({ data }: Props) {
  const cards = [
    { label: 'Total Posts', value: data.total_posts.toLocaleString(), icon: Hash },
    { label: 'Channels', value: data.channels.toLocaleString(), icon: Radio },
    { label: 'Date Range', value: 'Sep–Dec 2025', icon: Calendar },
    {
      label: 'Raw Declining Signals',
      value: data.declining_trends_found.toLocaleString(),
      icon: TrendingDown,
    },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {cards.map(({ label, value, icon: Icon }) => (
        <div
          key={label}
          className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800/60"
        >
          <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wide">
            <Icon size={14} />
            {label}
          </div>
          <div className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-50">
            {value}
          </div>
        </div>
      ))}
    </div>
  );
}
