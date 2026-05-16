"""
Main preprocessing pipeline.

Flow:
  CSV → SQLite in-memory → text cleaning → n-gram extraction →
  trend scoring (normalized) → JSON artifacts

Usage:
  python -m data_processing.scripts.ingest_and_compute --csv /path/to/telegram.csv --output ./artifacts
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_processing.loaders.telegram_csv_loader import TelegramCsvLoader
from data_processing.services.text_cleaning import clean_text, tokenize, is_alert_post, is_boilerplate_ngram
from data_processing.services.ngram_extraction import extract_ngrams
from data_processing.services.trend_scoring import compute_trend_scores
from data_processing.services.topic_consolidation import (
    build_topic_post_index,
    consolidate_trends,
)
from data_processing.services.topic_quality import apply_display_quality
from data_processing.services.artifact_writer import write_all_artifacts


def create_db_schema(conn: sqlite3.Connection):
    """Create the in-memory SQLite schema for posts."""
    conn.execute("""
        CREATE TABLE posts (
            id TEXT PRIMARY KEY,
            published_at TEXT NOT NULL,
            month TEXT NOT NULL,
            content TEXT NOT NULL,
            source_name TEXT NOT NULL,
            source_id TEXT NOT NULL,
            source_type TEXT NOT NULL
        )
    """)
    conn.execute("CREATE INDEX idx_posts_month ON posts(month)")
    conn.execute("CREATE INDEX idx_posts_source ON posts(source_name)")


def ingest_to_sqlite(csv_path: str, conn: sqlite3.Connection) -> int:
    """Load CSV into SQLite in-memory. Returns row count."""
    loader = TelegramCsvLoader(csv_path)
    count = 0
    batch = []
    batch_size = 10000

    for post in loader.load():
        month = post.published_at.strftime("%Y-%m")
        batch.append((
            post.id, post.published_at.isoformat(), month,
            post.content, post.source_name, post.source_id, post.source_type,
        ))
        count += 1
        if len(batch) >= batch_size:
            conn.executemany(
                "INSERT OR IGNORE INTO posts VALUES (?, ?, ?, ?, ?, ?, ?)", batch
            )
            batch = []

    if batch:
        conn.executemany(
            "INSERT OR IGNORE INTO posts VALUES (?, ?, ?, ?, ?, ?, ?)", batch
        )
    conn.commit()
    return count


def compute_monthly_ngrams(conn: sqlite3.Connection) -> tuple[
    dict[str, dict[str, int]],  # ngram -> {month: count}
    dict[str, int],              # month -> total posts
    dict[str, dict[str, dict[str, int]]],  # channel -> ngram -> {month: count}
    dict[str, dict[str, int]],   # channel -> {month: total}
]:
    """
    Extract n-grams per month and per channel.
    Returns global and channel-level monthly n-gram counts.
    """
    # Global counters
    monthly_ngram_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    monthly_totals: dict[str, int] = defaultdict(int)

    # Channel-level counters
    channel_ngram_counts: dict[str, dict[str, dict[str, int]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(int))
    )
    channel_monthly_totals: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    cursor = conn.execute("SELECT month, content, source_name FROM posts")
    alert_count = 0

    for month, content, channel in cursor:
        monthly_totals[month] += 1
        channel_monthly_totals[channel][month] += 1

        # Skip Home Front Command alert posts — they are location lists, not topical content
        if is_alert_post(content):
            alert_count += 1
            continue

        cleaned = clean_text(content)
        tokens = tokenize(cleaned)
        ngrams = extract_ngrams(tokens, max_n=2)

        # Deduplicate within a single post to avoid inflating counts
        unique_ngrams = set(ngrams)

        for ng in unique_ngrams:
            if is_boilerplate_ngram(ng):
                continue
            monthly_ngram_counts[ng][month] += 1
            channel_ngram_counts[channel][ng][month] += 1

    print(f"  Filtered {alert_count:,} alert posts from n-gram extraction")

    return (
        dict(monthly_ngram_counts),
        dict(monthly_totals),
        dict(channel_ngram_counts),
        dict(channel_monthly_totals),
    )


def find_representative_posts(
    conn: sqlite3.Connection, topics: list[str], max_per_topic: int = 3
) -> dict[str, list[dict]]:
    """Find example posts for each top trend topic."""
    representatives: dict[str, list[dict]] = {}

    for topic in topics:
        # Search for posts containing the topic phrase in September
        search_term = f"%{topic}%"
        cursor = conn.execute(
            """
            SELECT id, published_at, content, source_name
            FROM posts
            WHERE month = '2025-09' AND LOWER(content) LIKE ?
            LIMIT ?
            """,
            (search_term, max_per_topic),
        )
        posts = []
        for row in cursor:
            # Truncate long content for the artifact
            content = row[2][:500] + "..." if len(row[2]) > 500 else row[2]
            posts.append({
                "id": row[0],
                "published_at": row[1],
                "content": content,
                "channel": row[3],
            })
        representatives[topic] = posts

    return representatives


def compute_channel_breakdown(
    channel_ngram_counts: dict[str, dict[str, dict[str, int]]],
    channel_monthly_totals: dict[str, dict[str, int]],
    top_topics: list[str],
    top_n_channels: int = 10,
) -> dict[str, list[dict]]:
    """
    For each top topic, find which channels showed the strongest decline.
    """
    breakdown: dict[str, list[dict]] = {}

    for topic in top_topics:
        channel_scores = []
        for channel, ngram_data in channel_ngram_counts.items():
            if topic not in ngram_data:
                continue
            month_data = ngram_data[topic]
            totals = channel_monthly_totals[channel]

            sep_count = month_data.get("2025-09", 0)
            dec_count = month_data.get("2025-12", 0)
            sep_total = totals.get("2025-09", 0)
            dec_total = totals.get("2025-12", 0)

            if sep_count < 5 or sep_total == 0:
                continue

            sep_share = sep_count / sep_total
            dec_share = dec_count / dec_total if dec_total > 0 else 0

            if sep_share <= dec_share:
                continue

            decline_pct = (sep_share - dec_share) / sep_share

            channel_scores.append({
                "channel": channel,
                "sep_mentions": sep_count,
                "dec_mentions": dec_count,
                "sep_share": round(sep_share, 6),
                "dec_share": round(dec_share, 6),
                "decline_percentage": round(decline_pct, 4),
            })

        channel_scores.sort(key=lambda x: x["decline_percentage"], reverse=True)
        breakdown[topic] = channel_scores[:top_n_channels]

    return breakdown


def build_methodology() -> dict:
    """Document the scoring methodology for transparency."""
    return {
        "description": "Deterministic trend detection based on normalized n-gram frequency analysis.",
        "ranking": (
            "Trends are ranked by normalized September-to-December decline, weighted by September "
            "topic share to avoid over-ranking tiny low-volume topics that happen to vanish entirely."
        ),
        "steps": [
            "1. Load posts into SQLite in-memory database.",
            "2. Skip Home Front Command alert posts — these are location lists, not topical content.",
            "3. Clean text: lowercase, remove URLs, strip punctuation.",
            "4. Tokenize and extract unigrams + bigrams per post. Drop stopwords and UI boilerplate tokens.",
            "5. Deduplicate n-grams within each post (a post mentioning 'ceasefire' 5 times counts as 1).",
            "6. Compute monthly_share = posts_mentioning_ngram / total_posts_in_month.",
            "7. Compute decline_percentage = (sep_share - dec_share) / sep_share.",
            "8. Compute ranking_score = absolute_delta × decline_percentage (decline weighted by significance).",
            "9. Filter: min 50 September mentions, min 0.05% share, min 30% decline.",
            "10. Consolidate duplicate lexical signals only when reciprocal post-level overlap is strong.",
            "11. Recompute consolidated group metrics from unique post IDs to avoid double counting.",
            "12. Mark generic or duplicate-looking signals for display quality without deleting them.",
        ],
        "normalization": (
            "Raw counts are misleading because September has 224K posts while December has 83K. "
            "We normalize by computing each topic's share of monthly volume, making months comparable."
        ),
        "filters_applied": {
            "alert_posts_excluded": (
                "Posts matching Home Front Command alert templates (rocket alerts, "
                "evacuation orders) are excluded from n-gram extraction. They are long "
                "comma-separated location lists, not topical content."
            ),
            "stopwords": "Common English words (the, is, and, ...) are removed.",
            "boilerplate_tokens": (
                "UI/navigation tokens embedded in shared posts (reading, mobile, device, "
                "click, subscribe, ...) are removed because they reflect post formatting, "
                "not subject matter."
            ),
            "junk_tokens": "Long alphanumeric strings that look like URL fragments or hashes are removed.",
        },
        "thresholds": {
            "min_sep_mentions": 50,
            "min_sep_share": 0.0005,
            "min_decline_percentage": 0.30,
        },
        "consolidation": {
            "candidate_pool": "Top declining raw lexical signals only, default 200.",
            "merge_rule": (
                "Pairs are compared only when lexically plausible, then merged only with strong "
                "Jaccard overlap, reciprocal directional coverage, and similar monthly patterns."
            ),
            "broad_narrow_protection": (
                "Substring or broad/narrow pairs require stronger reciprocal coverage and comparable "
                "post volumes. One-directional containment is not enough."
            ),
            "double_counting": (
                "Merged groups use the union of matched post IDs per month and channel. Counts are "
                "never summed across member signals."
            ),
        },
        "display_quality": {
            "description": (
                "A deterministic display-only pass marks weak standalone terms, partial phrase "
                "fragments, and duplicate token-set variants so the dashboard can prefer topic-like "
                "groups. Analytical artifacts remain intact."
            ),
            "principle": (
                "Genericness is conservative and is not the same as being a unigram: real topics "
                "such as hostages, qatar, gaza, hamas, houthi, trump, and kirk remain displayable."
            ),
        },
        "limitations": [
            "N-gram matching is lexical, not semantic — different phrasings of the same concept are counted separately.",
            "Consolidation is conservative — some near-duplicates may remain separate if overlap evidence is not strong enough.",
            "Translation quality affects accuracy — the source data is machine-translated.",
            "No deduplication of cross-posted content across channels.",
        ],
    }


def load_existing_ai_labels(output_dir: Path) -> dict | None:
    """
    Load existing labels only as optional pair-discovery hints.

    Labels never cause a merge on their own; post-level overlap must still pass
    deterministic thresholds.
    """
    labels_path = output_dir / "ai_labels.json"
    if not labels_path.exists():
        return None
    try:
        with open(labels_path, "r", encoding="utf-8") as f:
            labels = json.load(f)
        print("  Found existing ai_labels.json; using labels only as optional consolidation hints")
        return labels
    except (OSError, json.JSONDecodeError):
        print("  Existing ai_labels.json could not be read; consolidation will ignore AI label hints")
        return None


def main():
    parser = argparse.ArgumentParser(description="SignalDrop preprocessing pipeline")
    parser.add_argument("--csv", required=True, help="Path to the Telegram CSV file")
    parser.add_argument("--output", default="./artifacts", help="Output directory for JSON artifacts")
    parser.add_argument("--top-n", type=int, default=30, help="Number of top trends to include")
    parser.add_argument(
        "--consolidation-candidates",
        type=int,
        default=200,
        help="Number of top raw declining signals considered for deterministic consolidation",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)
    print(f"[SignalDrop] Starting preprocessing pipeline")
    print(f"  CSV: {args.csv}")
    print(f"  Output: {output_dir}")
    print(f"  Top N trends: {args.top_n}")
    print(f"  Consolidation candidate pool: {args.consolidation_candidates}")

    # Step 1: Load into SQLite in-memory
    t0 = time.time()
    conn = sqlite3.connect(":memory:")
    create_db_schema(conn)
    row_count = ingest_to_sqlite(args.csv, conn)
    print(f"  [{time.time()-t0:.1f}s] Loaded {row_count:,} posts into SQLite")

    # Step 2: Extract n-grams per month
    t1 = time.time()
    monthly_ngram_counts, monthly_totals, channel_ngram_counts, channel_monthly_totals = (
        compute_monthly_ngrams(conn)
    )
    print(f"  [{time.time()-t1:.1f}s] Extracted n-grams. Unique n-grams: {len(monthly_ngram_counts):,}")
    print(f"  Monthly totals: {dict(sorted(monthly_totals.items()))}")

    # Step 3: Score trends
    t2 = time.time()
    scores = compute_trend_scores(monthly_ngram_counts, monthly_totals)
    print(f"  [{time.time()-t2:.1f}s] Computed {len(scores):,} declining trends")

    top_scores = scores[:args.top_n]
    top_topics = [s.topic for s in top_scores]

    # Step 4: Consolidate duplicate lexical signals using temporary post ID sets.
    t3 = time.time()
    candidate_scores = scores[:args.consolidation_candidates]
    candidate_topics = [s.topic for s in candidate_scores]
    post_index = build_topic_post_index(conn, candidate_topics)
    existing_ai_labels = load_existing_ai_labels(output_dir)
    consolidated_trends = consolidate_trends(
        raw_scores=candidate_scores,
        monthly_totals=monthly_totals,
        channel_monthly_totals=channel_monthly_totals,
        post_index=post_index,
        top_n=args.top_n,
        ai_labels=existing_ai_labels,
    )
    consolidated_trends = apply_display_quality(consolidated_trends)
    merged_groups = sum(1 for group in consolidated_trends if len(group["member_topics"]) > 1)
    displayable_groups = sum(1 for group in consolidated_trends if group.get("is_displayable", True))
    print(
        f"  [{time.time()-t3:.1f}s] Consolidated {len(candidate_scores):,} raw signals "
        f"into {len(consolidated_trends):,} top groups ({merged_groups} merged groups)"
    )

    # Step 5: Get representative posts for raw fallback artifacts
    t4 = time.time()
    representatives = find_representative_posts(conn, top_topics)
    print(f"  [{time.time()-t4:.1f}s] Found representative posts")

    # Step 6: Channel breakdown for raw fallback artifacts
    t5 = time.time()
    channel_breakdown = compute_channel_breakdown(
        channel_ngram_counts, channel_monthly_totals, top_topics
    )
    print(f"  [{time.time()-t5:.1f}s] Computed channel breakdown")

    # Step 7: Build artifacts
    overview = {
        "total_posts": row_count,
        "channels": len(set(
            row[0] for row in conn.execute("SELECT DISTINCT source_name FROM posts")
        )),
        "date_range": {
            "start": conn.execute("SELECT MIN(published_at) FROM posts").fetchone()[0],
            "end": conn.execute("SELECT MAX(published_at) FROM posts").fetchone()[0],
        },
        "monthly_volumes": dict(sorted(monthly_totals.items())),
        "declining_trends_found": len(scores),
        "top_trends_included": len(top_scores),
        "consolidated_trends_included": len(consolidated_trends),
        "consolidated_groups_merged": merged_groups,
        "displayable_trends_included": displayable_groups,
    }

    trends_data = [
        {
            "rank": i + 1,
            "topic": s.topic,
            "sep_mentions": s.sep_mentions,
            "dec_mentions": s.dec_mentions,
            "sep_share": round(s.sep_share, 6),
            "dec_share": round(s.dec_share, 6),
            "absolute_delta": round(s.absolute_delta, 6),
            "decline_percentage": round(s.decline_percentage, 4),
            "ranking_score": round(s.ranking_score, 8),
        }
        for i, s in enumerate(top_scores)
    ]

    timeseries_data = {
        s.topic: {
            "monthly_shares": {k: round(v, 6) for k, v in s.monthly_shares.items()},
            "monthly_mentions": s.monthly_mentions,
        }
        for s in top_scores
    }

    methodology = build_methodology()

    # Write all artifacts
    paths = write_all_artifacts(
        output_dir=output_dir,
        overview=overview,
        trends=trends_data,
        trend_timeseries=timeseries_data,
        channel_breakdown=channel_breakdown,
        representative_posts=representatives,
        methodology=methodology,
        consolidated_trends=consolidated_trends,
    )

    print(f"\n[SignalDrop] Done! Artifacts written to {output_dir}/")
    for name, path in paths.items():
        print(f"  {name}.json")

    conn.close()


if __name__ == "__main__":
    main()
