import type { Methodology } from '../types';

interface Props {
  data: Methodology;
}

export function MethodologyCard({ data }: Props) {
  return (
    <div className="bg-slate-800/50 border border-slate-700 rounded-xl p-6">
      <h2 className="text-xl font-semibold text-white mb-3">Methodology</h2>
      <p className="text-slate-400 text-sm mb-4">{data.description}</p>

      <div className="space-y-4">
        {data.ranking && (
          <div className="bg-indigo-500/10 border border-indigo-500/30 rounded-lg p-3">
            <h3 className="text-sm font-medium text-indigo-300 mb-1">Ranking Criterion</h3>
            <p className="text-slate-300 text-sm">{data.ranking}</p>
          </div>
        )}

        <div>
          <h3 className="text-sm font-medium text-slate-300 mb-2">Normalization</h3>
          <p className="text-slate-400 text-sm">{data.normalization}</p>
        </div>

        <div>
          <h3 className="text-sm font-medium text-slate-300 mb-2">Pipeline Steps</h3>
          <ol className="text-slate-400 text-sm space-y-1">
            {data.steps.map((step, i) => (
              <li key={i} className="ml-4">{step}</li>
            ))}
          </ol>
        </div>

        {data.filters_applied && (
          <div>
            <h3 className="text-sm font-medium text-slate-300 mb-2">Filters Applied</h3>
            <ul className="text-slate-400 text-sm space-y-2">
              {Object.entries(data.filters_applied).map(([key, value]) => (
                <li key={key}>
                  <span className="text-slate-300 font-medium capitalize">
                    {key.replace(/_/g, ' ')}:
                  </span>{' '}
                  {value}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div>
          <h3 className="text-sm font-medium text-slate-300 mb-2">Thresholds</h3>
          <div className="grid grid-cols-3 gap-2">
            {Object.entries(data.thresholds).map(([key, val]) => (
              <div key={key} className="bg-slate-900/50 rounded-lg p-2 text-center">
                <div className="text-xs text-slate-500">{key.replace(/_/g, ' ')}</div>
                <div className="text-sm font-mono text-white">{val}</div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h3 className="text-sm font-medium text-slate-300 mb-2">Known Limitations</h3>
          <ul className="text-slate-400 text-sm space-y-1 list-disc list-inside">
            {data.limitations.map((lim, i) => (
              <li key={i}>{lim}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
