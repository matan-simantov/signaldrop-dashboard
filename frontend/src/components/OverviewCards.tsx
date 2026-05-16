import { TrendingDown, Radio, Calendar, Hash } from 'lucide-react';
import type { Overview } from '../types';

interface Props {
  data: Overview;
}

export function OverviewCards({ data }: Props) {
  const cards = [
    { label: 'Total Posts', value: data.total_posts.toLocaleString(), icon: Hash },
    { label: 'Channels', value: data.channels.toLocaleString(), icon: Radio },
    { label: 'Date Range', value: `Sep–Dec 2025`, icon: Calendar },
    { label: 'Declining Trends', value: data.declining_trends_found.toLocaleString(), icon: TrendingDown },
  ];

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {cards.map(({ label, value, icon: Icon }) => (
        <div key={label} className="bg-slate-800/50 border border-slate-700 rounded-xl p-5">
          <div className="flex items-center gap-2 text-slate-400 text-sm mb-2">
            <Icon size={16} />
            {label}
          </div>
          <div className="text-2xl font-bold text-white">{value}</div>
        </div>
      ))}
    </div>
  );
}
