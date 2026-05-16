import { useEffect, useState } from 'react';
import { api } from './api/client';
import { OverviewCards } from './components/OverviewCards';
import { TrendChart } from './components/TrendChart';
import { TrendDetail } from './components/TrendDetail';
import { VolumeChart } from './components/VolumeChart';
import { MethodologyCard } from './components/MethodologyCard';
import type { Overview, Trend, TrendDetail as TrendDetailType, Methodology, AiLabels } from './types';

function App() {
  const [overview, setOverview] = useState<Overview | null>(null);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [methodology, setMethodology] = useState<Methodology | null>(null);
  const [aiLabels, setAiLabels] = useState<AiLabels>({});
  const [selectedTopic, setSelectedTopic] = useState<string | null>(null);
  const [trendDetail, setTrendDetail] = useState<TrendDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      api.getOverview(),
      api.getTrends(),
      api.getMethodology(),
      api.getAiLabels().catch(() => ({} as AiLabels)),
    ])
      .then(([ov, tr, meth, labels]) => {
        setOverview(ov);
        setTrends(tr);
        setMethodology(meth);
        setAiLabels(labels);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedTopic) {
      setTrendDetail(null);
      return;
    }
    api.getTrendDetail(selectedTopic).then(setTrendDetail).catch(console.error);
  }, [selectedTopic]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-slate-400 text-lg">Loading SignalDrop...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-red-400 text-lg">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6 md:p-10 max-w-7xl mx-auto space-y-8">
      {/* Header */}
      <header className="text-center space-y-2">
        <h1 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
          Signal<span className="text-indigo-400">Drop</span>
        </h1>
        <p className="text-slate-400 text-lg max-w-2xl mx-auto">
          A social intelligence dashboard detecting declining conversation trends across Telegram channels
        </p>
      </header>

      {/* Overview */}
      {overview && <OverviewCards data={overview} />}

      {/* Volume chart */}
      {overview && <VolumeChart volumes={overview.monthly_volumes} />}

      {/* Main trend chart */}
      <TrendChart
        trends={trends}
        aiLabels={aiLabels}
        onSelect={setSelectedTopic}
        selectedTopic={selectedTopic}
      />

      {/* Trend detail panel */}
      {trendDetail && <TrendDetail data={trendDetail} aiLabel={aiLabels[trendDetail.trend.topic]} />}

      {/* Methodology */}
      {methodology && <MethodologyCard data={methodology} />}

      {/* Footer */}
      <footer className="text-center text-slate-500 text-sm py-6 border-t border-slate-800">
        SignalDrop — Built for trend analysis of public Telegram data (Sep–Dec 2025)
      </footer>
    </div>
  );
}

export default App;
