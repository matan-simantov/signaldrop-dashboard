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
    <section className="rounded-xl border border-slate-200 bg-white p-6 dark:border-slate-700 dark:bg-slate-800/60">
      <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
        Monthly post volume
      </h2>
      <p className="mt-1 text-sm text-slate-600 dark:text-slate-400 max-w-3xl">
        Posting volume dropped sharply by December, so trends are ranked by share of monthly
        conversation rather than raw mention counts.
      </p>
      <div className="mt-4">
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
            <XAxis
              dataKey="month"
              stroke="#94a3b8"
              tick={{ fill: 'currentColor' }}
              className="text-slate-500 dark:text-slate-400"
            />
            <YAxis
              stroke="#94a3b8"
              tickFormatter={v => `${(v / 1000).toFixed(0)}k`}
              tick={{ fill: 'currentColor' }}
              className="text-slate-500 dark:text-slate-400"
            />
            <Tooltip
              cursor={{ fill: 'rgba(99, 102, 241, 0.08)' }}
              contentStyle={{
                backgroundColor: 'rgb(255 255 255)',
                border: '1px solid rgb(226 232 240)',
                borderRadius: 8,
                color: 'rgb(15 23 42)',
                fontSize: 12,
              }}
              formatter={((value: number) => [value.toLocaleString(), 'Posts']) as any}
            />
            <Bar dataKey="posts" fill="#4f46e5" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
