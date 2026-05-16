import type { Overview, Trend, TrendDetail, Methodology, AiLabels } from '../types';

// In local dev, '/api' is proxied to the backend by Vite (see vite.config.ts).
// In production builds, set VITE_API_BASE_URL to the deployed backend URL + /api,
// e.g. VITE_API_BASE_URL=https://abcde.eu-west-2.awsapprunner.com/api
const BASE = import.meta.env.VITE_API_BASE_URL || '/api';

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  getOverview: () => fetchJson<Overview>('/overview'),
  getTrends: () => fetchJson<Trend[]>('/trends'),
  getTrendDetail: (topic: string) => fetchJson<TrendDetail>(`/trends/${encodeURIComponent(topic)}`),
  getMethodology: () => fetchJson<Methodology>('/methodology'),
  getAiLabels: () => fetchJson<AiLabels>('/ai-labels'),
};
