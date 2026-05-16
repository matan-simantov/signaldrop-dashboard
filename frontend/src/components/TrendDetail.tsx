import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import type { TrendDetail as TrendDetailType, AiLabel } from '../types';

interface Props {
  data: TrendDetailType;
  aiLabel?: AiLabel;
}

const MONTH_LABELS: Record<string, string> = {
  '2025-09': 'Sep',
  '2025-10': 'Oct',
  '2025-11': 'Nov',
  '2025-12': 'Dec',
};

export function TrendDetail({ data, aiLabel }: Props) {
  const { trend, timeseries, channels, representative_posts } = data;

  const chartData = Object.entries(timeseries.monthly_shares)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, share]) => ({
      month: MONTH_LABELS[month] || month,
      share: +(share * 100).toFixed(3),
      mentions: timeseries.monthly_mentions[month],
    }));

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6 space-y-6">
      <div>
        <div className="flex items-baseline gap-3 flex-wrap">
          <h2 className="text-xl font-semibold text-white">
            {aiLabel?.label || `"${trend.topic}"`}
          </h2>
          {aiLabel?.category && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
              {aiLabel.category}
            </span>
          )}
          {aiLabel && (
            <span className="text-xs text-slate-500 font-mono">keyword: {trend.topic}</span>
          )}
        </div>
        {aiLabel?.explanation && (
          <p className="text-slate-300 text-sm mt-2 italic">{aiLabel.explanation}</p>
        )}
        <p className="text-slate-400 text-sm mt-2">
          {Math.round(trend.decline_percentage * 100)}% decline in normalized share from September to December
        </p>
      </div>

      {/* Time series chart */}
      <div>
        <h3 className="text-sm font-medium text-slate-300 mb-3">Monthly Share Trend (%)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
            <XAxis dataKey="month" stroke="#64748b" />
            <YAxis stroke="#64748b" tickFormatter={v => `${v}%`} />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
              labelStyle={{ color: '#f1f5f9' }}
              formatter={((value: number) => [`${value}%`, 'Share']) as any}
            />
            <Line
              type="monotone"
              dataKey="share"
              stroke="#f97316"
              strokeWidth={2}
              dot={{ fill: '#f97316', r: 4 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Comparison stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Sep Mentions" value={trend.sep_mentions.toLocaleString()} />
        <Stat label="Dec Mentions" value={trend.dec_mentions.toLocaleString()} />
        <Stat label="Sep Share" value={`${(trend.sep_share * 100).toFixed(2)}%`} />
        <Stat label="Dec Share" value={`${(trend.dec_share * 100).toFixed(2)}%`} />
      </div>

      {/* Channel breakdown */}
      {channels.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-slate-300 mb-3">Strongest Channel Declines</h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {channels.slice(0, 5).map(ch => (
              <div key={ch.channel} className="flex justify-between items-center text-sm bg-slate-900/50 rounded-lg px-3 py-2">
                <span className="text-slate-300 font-mono">@{ch.channel}</span>
                <span className="text-orange-400">{Math.round(ch.decline_percentage * 100)}% decline</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Representative posts */}
      {representative_posts.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-slate-300 mb-3">Example Posts (September)</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {representative_posts.map(post => (
              <div key={post.id} className="text-xs bg-slate-900/50 rounded-lg p-3 border border-slate-700/50">
                <div className="flex justify-between text-slate-500 mb-1">
                  <span>@{post.channel}</span>
                  <span>{new Date(post.published_at).toLocaleDateString()}</span>
                </div>
                <p className="text-slate-300 line-clamp-3">{post.content}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-slate-900/50 rounded-lg p-3 text-center">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-lg font-semibold text-white mt-1">{value}</div>
    </div>
  );
}
