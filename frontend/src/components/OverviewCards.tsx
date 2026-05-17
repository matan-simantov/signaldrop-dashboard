import { TrendingDown, Radio, Calendar, Hash } from 'lucide-react';
import type { Overview } from '../types';
import { InfoTooltip } from './InfoTooltip';

interface Props {
  data: Overview;
}

export function OverviewCards({ data }: Props) {
  const observed = data.observed_posts ?? data.total_posts;
  const canonical = data.total_posts;
  const showDedup = data.observed_posts !== undefined && data.observed_posts !== canonical;

  const postsValue = showDedup
    ? `${canonical.toLocaleString()}`
    : canonical.toLocaleString();
  const postsCaption = showDedup
    ? `unique cleaned text · ${observed.toLocaleString()} observed`
    : undefined;

  const cards = [
    {
      label: 'Posts (deduplicated)',
      value: postsValue,
      caption: postsCaption,
      icon: Hash,
      tooltip: showDedup
        ? 'Canonical (unique cleaned-text) posts after exact-content dedup. Verbatim copies across channels are collapsed.'
        : undefined,
    },
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
      {cards.map(({ label, value, caption, icon: Icon, tooltip }) => (
        <div
          key={label}
          className="rounded-xl border border-slate-200 bg-white p-5 dark:border-slate-700 dark:bg-slate-800/60"
        >
          <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400 text-xs uppercase tracking-wide">
            <Icon size={14} />
            <span>{label}</span>
            {tooltip && <InfoTooltip term={label} text={tooltip} />}
          </div>
          <div className="mt-2 text-2xl font-semibold text-slate-900 dark:text-slate-50">
            {value}
          </div>
          {caption && (
            <div className="mt-1 text-[11px] text-slate-500 dark:text-slate-400">
              {caption}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
