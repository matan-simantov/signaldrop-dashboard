import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
} from 'recharts';

interface Props {
  volumes: Record<string, number>;
}

const MONTH_LABELS: Record<string, string> = {
  '2025-09': 'Sep',
  '2025-10': 'Oct',
  '2025-11': 'Nov',
  '2025-12': 'Dec',
};

export function VolumeChart({ volumes }: Props) {
  const data = Object.entries(volumes)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([month, count]) => ({
      month: MONTH_LABELS[month] || month,
      posts: count,
    }));

  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
      <h2 className="text-xl font-semibold text-white mb-1">Monthly Post Volume</h2>
      <p className="text-slate-400 text-sm mb-4">
        Volume varies significantly — this is why we normalize by monthly total
      </p>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data}>
          <XAxis dataKey="month" stroke="#64748b" />
          <YAxis stroke="#64748b" tickFormatter={v => `${(v / 1000).toFixed(0)}k`} />
          <Tooltip
            contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: 8 }}
            labelStyle={{ color: '#f1f5f9' }}
            formatter={((value: number) => [value.toLocaleString(), 'Posts']) as any}
          />
          <Bar dataKey="posts" fill="#6366f1" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
