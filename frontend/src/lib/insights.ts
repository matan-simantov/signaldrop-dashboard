import type { Trend, AiLabels } from '../types';
import { resolveTrendLabel } from './labels';

export interface Insight {
  title: string;
  value: string;
  detail: string;
}

/**
 * Deterministic key findings derived from the existing trends + AI labels.
 * Every number comes straight from the trend data. Wording carefully separates
 * raw mention counts from normalized share changes so the two cannot be
 * conflated.
 */
export function deriveKeyFindings(trends: Trend[], aiLabels: AiLabels): Insight[] {
  if (trends.length === 0) return [];

  const findings: Insight[] = [];

  // 1. Sharpest relative decline (highest normalized decline %).
  const sharpest = [...trends].sort(
    (a, b) => b.decline_percentage - a.decline_percentage,
  )[0];
  findings.push({
    title: 'Sharpest relative decline',
    value: `${Math.round(sharpest.decline_percentage * 100)}%`,
    detail:
      `${resolveTrendLabel(sharpest, aiLabels)} nearly disappeared by December, ` +
      `dropping from ${(sharpest.sep_share * 100).toFixed(2)}% to ` +
      `${(sharpest.dec_share * 100).toFixed(2)}% of monthly conversation. ` +
      `This is the sharpest relative drop in the ranking — not necessarily the most central topic overall.`,
  });

  // 2. Highest September volume (most discussed declining topic). Make it
  //    explicit that the percentage refers to normalized share, not raw mentions.
  const mostDiscussed = [...trends].sort((a, b) => b.sep_mentions - a.sep_mentions)[0];
  findings.push({
    title: 'Highest September volume',
    value: resolveTrendLabel(mostDiscussed, aiLabels),
    detail:
      `Raw mentions fell from ${mostDiscussed.sep_mentions.toLocaleString()} to ` +
      `${mostDiscussed.dec_mentions.toLocaleString()}, while normalized share declined ` +
      `from ${(mostDiscussed.sep_share * 100).toFixed(2)}% to ` +
      `${(mostDiscussed.dec_share * 100).toFixed(2)}% ` +
      `(a ${Math.round(mostDiscussed.decline_percentage * 100)}% relative drop in share).`,
  });

  // 3. Largest absolute drop in share of voice (in percentage points).
  const largestShareDrop = [...trends].sort(
    (a, b) => b.absolute_delta - a.absolute_delta,
  )[0];
  const pts = (largestShareDrop.absolute_delta * 100).toFixed(2);
  findings.push({
    title: 'Largest share-of-voice drop',
    value: `−${pts} percentage points`,
    detail:
      `${resolveTrendLabel(largestShareDrop, aiLabels)} lost ${pts} percentage points ` +
      `of monthly conversation share between September and December — the largest absolute drop ` +
      `among ranked topics.`,
  });

  return findings;
}
