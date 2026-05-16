import type { Trend, AiLabels } from '../types';

export function resolveLabel(topic: string, aiLabels: AiLabels): string {
  const entry = aiLabels[topic];
  return entry?.short_label || entry?.label || topic;
}

/**
 * Filter the top trends so the main view doesn't show two rows with the same
 * AI label (e.g. "Charlie Kirk Shooting" vs "Charlie Kirk Attack"). Keeps the
 * highest-ranked occurrence and drops later duplicates. Full data remains
 * available via the underlying trends array for the detail panel.
 */
export function dedupeByLabel(trends: Trend[], aiLabels: AiLabels, limit = 10): Trend[] {
  const seen = new Set<string>();
  const out: Trend[] = [];
  for (const t of trends) {
    const key = resolveLabel(t.topic, aiLabels).trim().toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(t);
    if (out.length >= limit) break;
  }
  return out;
}
