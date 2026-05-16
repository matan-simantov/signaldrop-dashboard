import { useEffect, useMemo, useState } from 'react';
import { ArrowLeft } from 'lucide-react';
import { api } from './api/client';
import { Header } from './components/Header';
import { HomeScreen } from './components/HomeScreen';
import { KeyFindings } from './components/KeyFindings';
import { OverviewCards } from './components/OverviewCards';
import { TrendList } from './components/TrendList';
import { TrendDetail } from './components/TrendDetail';
import { VolumeChart } from './components/VolumeChart';
import { MethodologyCard } from './components/MethodologyCard';
import { useTheme } from './hooks/useTheme';
import { dedupeByLabel } from './lib/labels';
import { deriveKeyFindings } from './lib/insights';
import type { Overview, Trend, TrendDetail as TrendDetailType, Methodology, AiLabels, AiInsights } from './types';

type View = 'home' | 'telegram';

function readViewFromHash(): View {
  if (typeof window === 'undefined') return 'home';
  return window.location.hash === '#telegram' ? 'telegram' : 'home';
}

function App() {
  const { theme, toggle } = useTheme();
  const [view, setView] = useState<View>(readViewFromHash);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [methodology, setMethodology] = useState<Methodology | null>(null);
  const [aiLabels, setAiLabels] = useState<AiLabels>({});
  const [aiInsights, setAiInsights] = useState<AiInsights>({});
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
      api.getAiInsights().catch(() => ({} as AiInsights)),
    ])
      .then(([ov, tr, meth, labels, insights]) => {
        setOverview(ov);
        setTrends(tr);
        setMethodology(meth);
        setAiLabels(labels);
        setAiInsights(insights);
        setLoading(false);
      })
      .catch(err => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    if (!selectedTopic) return;
    let active = true;
    api.getTrendDetail(selectedTopic)
      .then(detail => {
        if (active) setTrendDetail(detail);
      })
      .catch(console.error);
    return () => {
      active = false;
    };
  }, [selectedTopic]);

  // Sync view ↔ hash (so refresh on #telegram stays on dashboard, but the
  // default with no hash always lands on home).
  useEffect(() => {
    const desiredHash = view === 'telegram' ? '#telegram' : '';
    if (window.location.hash !== desiredHash) {
      // Use replaceState so we don't pollute browser history per click.
      const url = `${window.location.pathname}${window.location.search}${desiredHash}`;
      window.history.replaceState(null, '', url);
    }
  }, [view]);

  useEffect(() => {
    const onHashChange = () => setView(readViewFromHash());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const usesConsolidatedTrends = useMemo(
    () => trends.some(t => Boolean(t.group_id || t.member_topics)),
    [trends],
  );

  const handleSelectTrend = (topic: string) => {
    setSelectedTopic(topic);
    setTrendDetail(null);
  };

  const handleCloseTrend = () => {
    setSelectedTopic(null);
    setTrendDetail(null);
  };

  const handleOpenTelegram = () => {
    setView('telegram');
    // Scroll to top so the user lands at the dashboard header.
    window.scrollTo({ top: 0, behavior: 'auto' });
  };

  const handleBackToDatasets = () => {
    setSelectedTopic(null);
    setTrendDetail(null);
    setView('home');
    window.scrollTo({ top: 0, behavior: 'auto' });
  };

  // Prefer displayable consolidated groups in the main list. The full artifact
  // remains available through the API.
  const visibleTrends = useMemo(
    () => {
      if (!usesConsolidatedTrends) return dedupeByLabel(trends, aiLabels, 10);
      return dedupeByLabel(
        trends.filter(t => t.is_displayable !== false),
        aiLabels,
        10,
      );
    },
    [trends, aiLabels, usesConsolidatedTrends],
  );

  const keyFindings = useMemo(
    () => (
      aiInsights.findings?.length
        ? aiInsights.findings
        : deriveKeyFindings(visibleTrends, aiLabels)
    ),
    [visibleTrends, aiLabels, aiInsights],
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
        <Header theme={theme} onToggleTheme={toggle} variant={view} />

        {view === 'home' && <HomeScreen onOpenTelegram={handleOpenTelegram} />}

        {view === 'telegram' && (
          <>
            <button
              type="button"
              onClick={handleBackToDatasets}
              className="inline-flex items-center gap-1.5 text-sm text-slate-600 hover:text-slate-900 transition dark:text-slate-300 dark:hover:text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-400 rounded px-1 -mx-1"
            >
              <ArrowLeft size={14} />
              Back to datasets
            </button>

            <main id="dashboard" className="space-y-10 scroll-mt-6">
              <KeyFindings
                headline={aiInsights.findings?.length ? aiInsights.headline : undefined}
                findings={keyFindings}
                caveat={aiInsights.findings?.length ? aiInsights.caveat : undefined}
              />

              {overview && <OverviewCards data={overview} />}

              <TrendList
                trends={visibleTrends}
                aiLabels={aiLabels}
                onSelect={handleSelectTrend}
                selectedTopic={selectedTopic}
              />

              {trendDetail && (
                <TrendDetail
                  data={trendDetail}
                  onClose={handleCloseTrend}
                  aiLabel={
                    aiLabels[trendDetail.trend.topic] ||
                    (trendDetail.trend.representative_topic
                      ? aiLabels[trendDetail.trend.representative_topic]
                      : undefined)
                  }
                />
              )}

              {overview && <VolumeChart volumes={overview.monthly_volumes} />}

              {methodology && <MethodologyCard data={methodology} />}
            </main>

            <p className="text-xs text-slate-500 dark:text-slate-400 text-center max-w-3xl mx-auto">
              AI summarizes deterministic trend outputs and generates readable labels. It does not
              calculate rankings, counts, shares, decline metrics, or topic groups.
            </p>
          </>
        )}

        <footer className="text-center text-xs text-slate-400 dark:text-slate-500 py-6 border-t border-slate-200 dark:border-slate-800">
          SignalDrop · public conversation trend analysis
        </footer>
      </div>
    </div>
  );
}

export default App;
