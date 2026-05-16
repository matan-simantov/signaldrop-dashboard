import { useEffect, useMemo, useState } from 'react';
import { api } from './api/client';
import { Header } from './components/Header';
import { KeyFindings } from './components/KeyFindings';
import { OverviewCards } from './components/OverviewCards';
import { TrendList } from './components/TrendList';
import { TrendDetail } from './components/TrendDetail';
import { VolumeChart } from './components/VolumeChart';
import { MethodologyCard } from './components/MethodologyCard';
import { useTheme } from './hooks/useTheme';
import { dedupeByLabel } from './lib/labels';
import { deriveKeyFindings } from './lib/insights';
import type { Overview, Trend, TrendDetail as TrendDetailType, Methodology, AiLabels } from './types';

function App() {
  const { theme, toggle } = useTheme();
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

  // Dedup the main list so multiple keywords mapped to the same AI label don't
  // dominate the top 10. Full trend data remains available via the detail panel.
  const visibleTrends = useMemo(
    () => dedupeByLabel(trends, aiLabels, 10),
    [trends, aiLabels],
  );

  const keyFindings = useMemo(
    () => deriveKeyFindings(visibleTrends, aiLabels),
    [visibleTrends, aiLabels],
  );

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <div className="text-slate-500 dark:text-slate-400 text-lg">Loading SignalDrop…</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-slate-950">
        <div className="text-rose-600 dark:text-rose-400 text-lg">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 md:py-12 space-y-10">
        <Header overview={overview} theme={theme} onToggleTheme={toggle} />

        <KeyFindings findings={keyFindings} />

        {overview && <OverviewCards data={overview} />}

        <TrendList
          trends={visibleTrends}
          aiLabels={aiLabels}
          onSelect={setSelectedTopic}
          selectedTopic={selectedTopic}
        />

        {trendDetail && (
          <TrendDetail data={trendDetail} aiLabel={aiLabels[trendDetail.trend.topic]} />
        )}

        {overview && <VolumeChart volumes={overview.monthly_volumes} />}

        {methodology && <MethodologyCard data={methodology} />}

        <p className="text-xs text-slate-500 dark:text-slate-400 text-center max-w-3xl mx-auto">
          AI is used only to generate readable labels and explanations. Trend ranking is fully
          deterministic and based on normalized September-to-December share of conversation.
        </p>

        <footer className="text-center text-xs text-slate-400 dark:text-slate-500 py-6 border-t border-slate-200 dark:border-slate-800">
          SignalDrop · public Telegram trend analysis · Sep–Dec 2025
        </footer>
      </div>
    </div>
  );
}

export default App;
