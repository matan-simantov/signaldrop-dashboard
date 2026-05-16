"""
Core trend detection logic.

A "declining trend" is an n-gram whose normalized share of monthly posts
decreased significantly from September to December.

Scoring methodology:
1. monthly_share = topic_mentions_in_month / total_posts_in_month
   Normalizes for volume differences between months. September has 224K posts,
   December has 83K — raw counts alone are misleading.
2. decline_percentage = (sep_share - dec_share) / sep_share
   How much of the September signal was lost by December.
3. ranking_score = absolute_delta * decline_percentage
   The ranking criterion: normalized Sep-to-Dec decline weighted by September
   topic share. Pure decline_percentage alone over-ranks tiny topics that
   happen to vanish entirely.
4. Threshold filters remove low-volume noise.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TrendScore:
    topic: str
    sep_mentions: int
    dec_mentions: int
    sep_share: float
    dec_share: float
    absolute_delta: float
    decline_percentage: float
    ranking_score: float
    monthly_shares: dict[str, float]
    monthly_mentions: dict[str, int]


def compute_trend_scores(
    monthly_counts: dict[str, dict[str, int]],
    monthly_totals: dict[str, int],
    min_sep_mentions: int = 50,
    min_sep_share: float = 0.0005,
    min_decline_pct: float = 0.3,
) -> list[TrendScore]:
    """
    Compute declining trend scores for all n-grams.

    Args:
        monthly_counts: {ngram: {month: count}} e.g. {"ceasefire": {"2025-09": 400, ...}}
        monthly_totals: {month: total_posts} e.g. {"2025-09": 224813, ...}
        min_sep_mentions: Minimum mentions in September to qualify
        min_sep_share: Minimum September share to filter noise
        min_decline_pct: Minimum decline percentage (0.3 = 30% decline)

    Returns:
        List of TrendScore objects, sorted by ranking_score descending.
    """
    sep_key = "2025-09"
    dec_key = "2025-12"
    all_months = sorted(monthly_totals.keys())

    if sep_key not in monthly_totals or dec_key not in monthly_totals:
        raise ValueError(f"Data must contain both September and December. Found: {list(monthly_totals.keys())}")

    scores: list[TrendScore] = []

    for ngram, month_data in monthly_counts.items():
        sep_count = month_data.get(sep_key, 0)
        dec_count = month_data.get(dec_key, 0)

        if sep_count < min_sep_mentions:
            continue

        sep_share = sep_count / monthly_totals[sep_key]
        dec_share = dec_count / monthly_totals[dec_key] if monthly_totals[dec_key] > 0 else 0

        if sep_share < min_sep_share:
            continue

        absolute_delta = sep_share - dec_share
        if absolute_delta <= 0:
            continue

        decline_pct = absolute_delta / sep_share

        if decline_pct < min_decline_pct:
            continue

        # ranking_score = decline weighted by September significance.
        # Without the weighting, tiny topics that drop to zero would dominate
        # the leaderboard at the expense of high-volume topics with real shifts.
        ranking = absolute_delta * decline_pct

        monthly_shares = {}
        monthly_mentions = {}
        for month in all_months:
            count = month_data.get(month, 0)
            monthly_mentions[month] = count
            monthly_shares[month] = count / monthly_totals[month] if monthly_totals[month] > 0 else 0

        scores.append(TrendScore(
            topic=ngram,
            sep_mentions=sep_count,
            dec_mentions=dec_count,
            sep_share=sep_share,
            dec_share=dec_share,
            absolute_delta=absolute_delta,
            decline_percentage=decline_pct,
            ranking_score=ranking,
            monthly_shares=monthly_shares,
            monthly_mentions=monthly_mentions,
        ))

    scores.sort(key=lambda s: s.ranking_score, reverse=True)
    return scores
