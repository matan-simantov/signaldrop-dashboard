import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import type { Trend, AiLabels } from '../types';

interface Props {
  trends: Trend[];
  aiLabels: AiLabels;
  onSelect: (topic: string) => void;
  selectedTopic: string | null;
}

export function TrendChart({ trends, aiLabels, onSelect, selectedTopic }: Props) {
  // Use AI label if available, otherwise fall back to deterministic topic keyword.
  const displayName = (topic: string) => aiLabels[topic]?.label || topic;

  const data = trends.slice(0, 15).map(t => ({
    topic: t.topic,
    displayName: displayName(t.topic),
    decline: Math.round(t.decline_percentage * 100),
    sepShare: (t.sep_share * 100).toFixed(2),
    decShare: (t.dec_share * 100).toFixed(2),
  }));

  // BarChart onClick is more reliable than Bar/Cell onClick across Recharts versions —
  // it receives the active item directly.
  const handleChartClick = (state: any) => {
    const topic = state?.activePayload?.[0]?.payload?.topic;
    if (topic) onSelect(topic);
  };

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
      <h2 className="text-xl font-semibold text-white mb-1">Top Declining Trends</h2>
      <p className="text-slate-400 text-sm mb-6">
        Ranked by normalized September-to-December decline, weighted by September topic share.
        Click a bar — or any row below — to see details.
      </p>
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={data}
          layout="vertical"
          margin={{ left: 120, right: 20 }}
          onClick={handleChartClick}
        >
          <XAxis type="number" domain={[0, 100]} tickFormatter={v => `${v}%`} stroke="#64748b" />
          <YAxis
            type="category"
            dataKey="displayName"
            tick={{ fill: '#e2e8f0', fontSize: 12 }}
            width={130}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            labelStyle={{ color: '#f1f5f9' }}
            formatter={((value: number, _name: string, props: { payload: { sepShare: string; decShare: string } }) => [
              `${value}% decline (Sep: ${props.payload.sepShare}% → Dec: ${props.payload.decShare}%)`,
              'Decline',
            ]) as any}
          />
          <Bar dataKey="decline" radius={[0, 4, 4, 0]} cursor="pointer">
            {data.map((entry) => (
              <Cell
                key={entry.topic}
                fill={entry.topic === selectedTopic ? '#f97316' : '#6366f1'}
                opacity={entry.topic === selectedTopic ? 1 : 0.8}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* Fallback clickable list — guaranteed-reliable trend selection */}
      <div className="mt-6 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {data.map(entry => {
          const isSelected = entry.topic === selectedTopic;
          return (
            <button
              key={entry.topic}
              onClick={() => onSelect(entry.topic)}
              className={`text-left text-sm rounded-lg px-3 py-2 border transition ${
                isSelected
                  ? 'bg-orange-500/15 border-orange-500/50 text-orange-200'
                  : 'bg-slate-900/40 border-slate-700/50 text-slate-300 hover:bg-slate-800 hover:border-slate-600'
              }`}
            >
              <div className="font-medium truncate">{entry.displayName}</div>
              <div className="text-xs text-slate-500 mt-0.5">{entry.decline}% decline</div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
