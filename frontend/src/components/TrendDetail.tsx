import { useState } from 'react';
import { X } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import type { TrendDetail as TrendDetailType, AiLabel } from '../types';
import { InfoTooltip } from './InfoTooltip';

interface Props {
  data: TrendDetailType;
  aiLabel?: AiLabel;
  onClose: () => void;
}

const MONTH_LABELS: Record<string, string> = {
  '2025-09': 'Sep',
  '2025-10': 'Oct',
  '2025-11': 'Nov',
  '2025-12': 'Dec',
};

const DEFAULT_POSTS_SHOWN = 3;

export function TrendDetail({ data, aiLabel, onClose }: Props) {
  const { trend, timeseries, channels, representative_posts } = data;
  const [showAllPosts, setShowAllPosts] = useState(false);

  const chartData = Object.entries(timeseries.monthly_shares)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, share]) => ({
      month: MONTH_LABELS[month] || month,
      share: +(share * 100).toFixed(3),
      mentions: timeseries.monthly_mentions[month],
    }));

  const title = aiLabel?.short_label || aiLabel?.label || trend.label || `"${trend.representative_topic || trend.topic}"`;
  const declinePct = Math.round(trend.decline_percentage * 100);
  const representativeSignal = trend.representative_topic || trend.topic;
  const relatedSignals = trend.member_topics || [representativeSignal];
  const isGrouped = relatedSignals.length > 1;
  const visiblePosts = showAllPosts
    ? representative_posts
    : representative_posts.slice(0, DEFAULT_POSTS_SHOWN);

  // Channel-level drops: only channels with at least 10 September mentions for
  // this topic (avoids one-off mentions dominating the list). Sort by absolute
  // mention drop first, then relative decline.
  const channelRows = channels
    .filter(ch => ch.sep_mentions >= 10)
    .map(ch => ({
      ...ch,
      absoluteDrop: ch.sep_mentions - ch.dec_mentions,
    }))
    .sort(
      (a, b) =>
        b.absoluteDrop - a.absoluteDrop ||
        b.decline_percentage - a.decline_percentage,
    )
    .slice(0, 6);

  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 md:p-8 space-y-8 dark:border-slate-700 dark:bg-slate-800/60">
      {/* Header */}
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-3 flex-wrap">
            <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100">{title}</h2>
            {aiLabel?.category && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-500/10 dark:text-indigo-300 dark:border-indigo-500/30">
                {aiLabel.category}
              </span>
            )}
            <span className="text-xs text-slate-500 font-mono dark:text-slate-400">
              signal: {representativeSignal}
            </span>
          </div>
          {isGrouped && (
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
              Grouped from {relatedSignals.length} related signals: {relatedSignals.join(', ')}
            </p>
          )}
          {aiLabel?.explanation && (
            <p className="mt-3 text-sm text-slate-600 dark:text-slate-300 leading-relaxed max-w-3xl">
              {aiLabel.explanation}
            </p>
          )}
          <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">
            Raw mentions fell from {trend.sep_mentions.toLocaleString()} to{' '}
            {trend.dec_mentions.toLocaleString()}, while normalized share declined from{' '}
            {(trend.sep_share * 100).toFixed(2)}% to {(trend.dec_share * 100).toFixed(2)}% — a{' '}
            {declinePct}% relative drop in share of monthly canonical posts.
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label="Close trend detail"
          className="shrink-0 inline-flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 text-slate-500 transition hover:bg-slate-50 hover:text-slate-900 focus:outline-none focus:ring-2 focus:ring-indigo-400 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-700 dark:hover:text-slate-100"
        >
          <X size={16} />
        </button>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Sep Mentions" value={trend.sep_mentions.toLocaleString()} />
        <Stat label="Dec Mentions" value={trend.dec_mentions.toLocaleString()} />
        <Stat label="Sep Share" value={`${(trend.sep_share * 100).toFixed(2)}%`} />
        <Stat label="Dec Share" value={`${(trend.dec_share * 100).toFixed(2)}%`} />
      </div>

      {/* Time series chart */}
      <div>
        <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300 mb-3">
          Monthly share (% of all posts that month)
        </h3>
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--chart-grid, #e2e8f0)" className="dark:[--chart-grid:#334155]" />
            <XAxis
              dataKey="month"
              stroke="#94a3b8"
              tick={{ fill: 'currentColor' }}
              className="text-slate-500 dark:text-slate-400"
            />
            <YAxis
              stroke="#94a3b8"
              tickFormatter={v => `${v}%`}
              tick={{ fill: 'currentColor' }}
              className="text-slate-500 dark:text-slate-400"
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'rgb(255 255 255)',
                border: '1px solid rgb(226 232 240)',
                borderRadius: 8,
                color: 'rgb(15 23 42)',
                fontSize: 12,
              }}
              formatter={value => [`${value}%`, 'Share']}
            />
            <Line
              type="monotone"
              dataKey="share"
              stroke="#4f46e5"
              strokeWidth={2}
              dot={{ fill: '#4f46e5', r: 4 }}
              activeDot={{ r: 6 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Channels — where this topic disappeared */}
      {channelRows.length > 0 && (
        <div>
          <div className="mb-3">
            <div className="flex items-center gap-1.5">
              <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">
                Channel-level drops
              </h3>
              <InfoTooltip
                term="first observed channel"
                text="Channel where this cleaned-text first appeared. Not the original source — the dataset has no forward metadata."
              />
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
              First-observed channels (after dedup) with at least 10 September mentions, sorted by
              largest mention drop.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {channelRows.map(ch => (
              <div
                key={ch.channel}
                className="flex items-center justify-between gap-3 rounded-lg px-3 py-2.5 bg-slate-50 border border-slate-200 dark:bg-slate-900/40 dark:border-slate-700"
              >
                <div className="min-w-0">
                  <div className="text-xs font-mono text-slate-700 dark:text-slate-300 truncate">
                    @{ch.channel}
                  </div>
                  <div className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                    {ch.sep_mentions.toLocaleString()} → {ch.dec_mentions.toLocaleString()} mentions
                  </div>
                </div>
                <div className="text-sm font-medium text-indigo-700 dark:text-indigo-300 shrink-0">
                  −{Math.round(ch.decline_percentage * 100)}%
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Posts */}
      {representative_posts.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-medium text-slate-700 dark:text-slate-300">
              Example posts (September)
            </h3>
            {representative_posts.length > DEFAULT_POSTS_SHOWN && (
              <button
                onClick={() => setShowAllPosts(v => !v)}
                className="text-xs text-indigo-600 hover:text-indigo-700 dark:text-indigo-400 dark:hover:text-indigo-300"
              >
                {showAllPosts ? 'Show fewer' : `Show all ${representative_posts.length}`}
              </button>
            )}
          </div>
          <div className="space-y-3">
            {visiblePosts.map(post => (
              <div
                key={post.id}
                className="rounded-lg p-4 bg-slate-50 border border-slate-200 dark:bg-slate-900/40 dark:border-slate-700"
              >
                <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400 mb-2">
                  <span className="font-mono">@{post.channel}</span>
                  <span>{new Date(post.published_at).toLocaleDateString()}</span>
                </div>
                <p className="text-sm text-slate-700 dark:text-slate-200 leading-relaxed line-clamp-4">
                  {post.content}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg p-3 bg-slate-50 border border-slate-200 dark:bg-slate-900/40 dark:border-slate-700">
      <div className="text-xs uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </div>
      <div className="mt-1 text-lg font-semibold text-slate-900 dark:text-slate-100">
        {value}
      </div>
    </div>
  );
}
