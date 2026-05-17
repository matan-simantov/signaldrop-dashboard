"""
Phase-1 analysis: measure exact cleaned-content duplicate impact.

Reads the raw CSV, applies `clean_text` (the same cleaning used by the pipeline),
hashes each cleaned text, and reports:
  - row count
  - unique cleaned texts (after dedup)
  - duplicate rows (rows that share a cleaned-text hash with another row)
  - short rows excluded from dedup (cleaned length < MIN_CONTENT_LENGTH)
  - top-N most-duplicated cleaned texts (with channel count and sample preview)
  - per-month duplicate impact
  - whether top deterministic trends would have shifted under dedup (lightweight check)

This script does NOT write artifacts. It only prints a report.

Usage:
  python -m data_processing.scripts.audit_duplicates --csv ~/Downloads/telegram.csv
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_processing.services.text_cleaning import clean_text, is_alert_post

MIN_CONTENT_LENGTH = 20


def hash_clean(content: str) -> str:
    return hashlib.sha1(clean_text(content).encode("utf-8")).hexdigest()


def main():
    parser = argparse.ArgumentParser(description="Audit exact-cleaned-content duplicates")
    parser.add_argument("--csv", required=True, help="Path to the Telegram CSV")
    parser.add_argument("--top", type=int, default=15, help="Top N duplicated texts to show")
    args = parser.parse_args()

    csv_path = Path(args.csv).expanduser()
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        sys.exit(2)

    hash_to_rows: dict[str, list[dict]] = defaultdict(list)
    hash_to_channels: dict[str, set[str]] = defaultdict(set)
    monthly_total = Counter()
    monthly_unique_hashes: dict[str, set[str]] = defaultdict(set)
    short_skipped = 0
    short_skipped_monthly = Counter()
    alert_rows = 0
    total_rows = 0

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_rows += 1
            content = row["translated_content"]
            try:
                month = row["dt_published"][:7]
            except KeyError:
                month = "unknown"
            monthly_total[month] += 1

            if is_alert_post(content):
                alert_rows += 1
                continue

            cleaned = clean_text(content)
            if len(cleaned) < MIN_CONTENT_LENGTH:
                short_skipped += 1
                short_skipped_monthly[month] += 1
                continue

            h = hashlib.sha1(cleaned.encode("utf-8")).hexdigest()
            hash_to_rows[h].append({
                "id": row["id"],
                "month": month,
                "channel": row["channel_name"],
                "preview": content[:120].replace("\n", " "),
            })
            hash_to_channels[h].add(row["channel_name"])
            monthly_unique_hashes[month].add(h)

    # ---- Summary ----
    unique_hashes = len(hash_to_rows)
    rows_in_hashes = sum(len(v) for v in hash_to_rows.values())
    duplicate_hashes = sum(1 for v in hash_to_rows.values() if len(v) > 1)
    duplicate_rows = sum(len(v) - 1 for v in hash_to_rows.values() if len(v) > 1)
    cross_channel_dup_hashes = sum(
        1 for h, rows in hash_to_rows.items()
        if len(rows) > 1 and len(hash_to_channels[h]) > 1
    )

    print("=" * 78)
    print("EXACT CLEANED-CONTENT DUPLICATE AUDIT")
    print("=" * 78)
    print()
    print(f"Total rows in CSV                          : {total_rows:,}")
    print(f"Alert-template rows skipped (HFC etc.)     : {alert_rows:,}")
    print(f"Short rows (<{MIN_CONTENT_LENGTH} chars cleaned) skipped : {short_skipped:,}")
    print(f"Rows considered for dedup                  : {rows_in_hashes:,}")
    print()
    print(f"Unique cleaned-text hashes                 : {unique_hashes:,}")
    print(f"Hashes with >1 row (duplicate groups)      : {duplicate_hashes:,}")
    print(f"  of which span multiple channels          : {cross_channel_dup_hashes:,}")
    print(f"Duplicate rows that would collapse         : {duplicate_rows:,}")
    print()
    if rows_in_hashes:
        pct = duplicate_rows / rows_in_hashes * 100
        print(f"% of considered rows that are duplicates   : {pct:.2f}%")
    print()
    print("Per-month breakdown:")
    print(f"{'month':<10} {'total_rows':>12} {'short_skip':>12} {'unique_hash':>14}")
    for month in sorted(monthly_total):
        print(
            f"{month:<10} {monthly_total[month]:>12,} "
            f"{short_skipped_monthly[month]:>12,} "
            f"{len(monthly_unique_hashes[month]):>14,}"
        )

    # ---- Top duplicated texts ----
    print()
    print("=" * 78)
    print(f"TOP {args.top} MOST-DUPLICATED CLEANED TEXTS")
    print("=" * 78)
    top = sorted(hash_to_rows.items(), key=lambda kv: len(kv[1]), reverse=True)[: args.top]
    for i, (h, rows) in enumerate(top, 1):
        channels = hash_to_channels[h]
        months = Counter(r["month"] for r in rows)
        preview = rows[0]["preview"]
        print(f"\n#{i} — {len(rows):,} rows in {len(channels)} channels")
        print(f"    months: {dict(months)}")
        print(f"    preview: {preview}{'...' if len(rows[0]['preview']) >= 120 else ''}")

    # ---- Sample translation-variance signal ----
    print()
    print("=" * 78)
    print("ROUGH SHORT-ROW DISTRIBUTION (would be skipped from dedup)")
    print("=" * 78)
    print(f"Short rows: {short_skipped:,}")
    print(f"(short means cleaned-length < {MIN_CONTENT_LENGTH} chars — typical: stickers, emoji-only, 1–2 word reactions)")


if __name__ == "__main__":
    main()
