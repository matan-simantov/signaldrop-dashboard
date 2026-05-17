"""
Deterministic topic consolidation based on post-level overlap.

The first-pass trend detector intentionally treats lexical n-grams as topic
signals. This module groups near-duplicate signals only when the underlying
post IDs prove they are the same conversation. Metrics are recomputed from
unique post IDs, never by summing member topic counts.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Iterable, Optional

from data_processing.services.ngram_extraction import extract_ngrams
from data_processing.services.text_cleaning import (
    clean_text,
    is_alert_post,
    is_boilerplate_ngram,
    tokenize,
)
from data_processing.services.trend_scoring import TrendScore


MIN_INTERSECTION_POSTS = 25
MIN_PATTERN_SIMILARITY = 0.88

GENERAL_MIN_JACCARD = 0.68
GENERAL_MIN_DIRECTIONAL_COVERAGE = 0.82

BROAD_NARROW_MIN_JACCARD = 0.78
BROAD_NARROW_MIN_DIRECTIONAL_COVERAGE = 0.90
BROAD_NARROW_MIN_TOTAL_SIZE_RATIO = 0.75
BROAD_NARROW_MIN_SEP_SIZE_RATIO = 0.75

ALIAS_MIN_JACCARD = 0.65
ALIAS_MIN_DIRECTIONAL_COVERAGE = 0.80

GENERIC_AI_LABEL_HINTS = frozenset({
    "social media platform mentions",
    "social platform coverage",
    "gaza city strike reports",
    "gaza war coverage",
    "rosh hashanah coverage",
})


@dataclass
class TopicPostIndex:
    topic_month_posts: dict[str, dict[str, set[str]]]
    topic_channel_month_posts: dict[str, dict[str, dict[str, set[str]]]]
    post_info: dict[str, dict[str, str]]


@dataclass
class MergeEvidence:
    merge: bool
    method: str
    confidence: float
    intersection_posts: int
    jaccard: float
    coverage_a_to_b: float
    coverage_b_to_a: float
    pattern_similarity: float
    summary: str


def build_topic_post_index(conn, candidate_topics: Iterable[str]) -> TopicPostIndex:
    """
    Rescan posts and store temporary post ID sets for candidate topics only.

    The index is intentionally temporary and is not written to JSON artifacts.
    """
    candidates = set(candidate_topics)
    topic_month_posts: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    topic_channel_month_posts: dict[str, dict[str, dict[str, set[str]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(set))
    )
    post_info: dict[str, dict[str, str]] = {}

    cursor = conn.execute(
        """
        SELECT id, published_at, month, content, source_name
        FROM posts
        WHERE is_canonical = 1
        """
    )
    for post_id, published_at, month, content, channel in cursor:
        if is_alert_post(content):
            continue

        cleaned = clean_text(content)
        tokens = tokenize(cleaned)
        ngrams = extract_ngrams(tokens, max_n=2)
        unique_ngrams = {
            ng for ng in ngrams
            if not is_boilerplate_ngram(ng)
        }
        matched_topics = unique_ngrams.intersection(candidates)
        if not matched_topics:
            continue

        post_info[post_id] = {
            "id": post_id,
            "published_at": published_at,
            "content": content,
            "channel": channel,
            "month": month,
        }
        for topic in matched_topics:
            topic_month_posts[topic][month].add(post_id)
            topic_channel_month_posts[topic][channel][month].add(post_id)

    return TopicPostIndex(
        topic_month_posts={k: dict(v) for k, v in topic_month_posts.items()},
        topic_channel_month_posts={
            topic: {channel: dict(months) for channel, months in channels.items()}
            for topic, channels in topic_channel_month_posts.items()
        },
        post_info=post_info,
    )


def consolidate_trends(
    raw_scores: list[TrendScore],
    monthly_totals: dict[str, int],
    channel_monthly_totals: dict[str, dict[str, int]],
    post_index: TopicPostIndex,
    top_n: int,
    ai_labels: Optional[dict[str, dict[str, str]]] = None,
) -> list[dict[str, Any]]:
    """
    Group raw trend signals conservatively and return final consolidated groups.
    """
    raw_by_topic = {score.topic: score for score in raw_scores}
    candidate_topics = [score.topic for score in raw_scores]
    candidate_set = set(candidate_topics)
    assigned: set[str] = set()
    provisional_groups: list[dict[str, Any]] = []

    for seed in candidate_topics:
        if seed in assigned:
            continue

        members = [seed]
        member_evidence: list[dict[str, Any]] = []

        for candidate in candidate_topics:
            if candidate == seed or candidate in assigned:
                continue
            if not _is_plausible_pair(seed, candidate, candidate_set, ai_labels):
                continue

            evidence = _evaluate_pair(seed, candidate, post_index, monthly_totals, ai_labels, candidate_set)
            if not evidence.merge:
                continue

            members.append(candidate)
            member_evidence.append({
                "topic": candidate,
                "method": evidence.method,
                "confidence": round(evidence.confidence, 3),
                "intersection_posts": evidence.intersection_posts,
                "jaccard": round(evidence.jaccard, 3),
                "coverage_with_representative": {
                    seed: round(evidence.coverage_a_to_b, 3),
                    candidate: round(evidence.coverage_b_to_a, 3),
                },
                "pattern_similarity": round(evidence.pattern_similarity, 3),
                "summary": evidence.summary,
            })

        assigned.update(members)
        group = _build_group(
            representative_topic=seed,
            members=members,
            raw_by_topic=raw_by_topic,
            monthly_totals=monthly_totals,
            channel_monthly_totals=channel_monthly_totals,
            post_index=post_index,
            member_evidence=member_evidence,
        )
        if group is not None:
            provisional_groups.append(group)

    provisional_groups.sort(key=lambda group: group["ranking_score"], reverse=True)

    final_groups = provisional_groups[:top_n]
    for rank, group in enumerate(final_groups, start=1):
        group["rank"] = rank
    return final_groups


def _build_group(
    representative_topic: str,
    members: list[str],
    raw_by_topic: dict[str, TrendScore],
    monthly_totals: dict[str, int],
    channel_monthly_totals: dict[str, dict[str, int]],
    post_index: TopicPostIndex,
    member_evidence: list[dict[str, Any]],
) -> Optional[dict[str, Any]]:
    all_months = sorted(monthly_totals.keys())
    monthly_post_sets: dict[str, set[str]] = {month: set() for month in all_months}

    for topic in members:
        for month in all_months:
            monthly_post_sets[month].update(post_index.topic_month_posts.get(topic, {}).get(month, set()))

    sep_count = len(monthly_post_sets.get("2025-09", set()))
    dec_count = len(monthly_post_sets.get("2025-12", set()))
    sep_total = monthly_totals.get("2025-09", 0)
    dec_total = monthly_totals.get("2025-12", 0)
    if sep_count == 0 or sep_total == 0:
        return None

    sep_share = sep_count / sep_total
    dec_share = dec_count / dec_total if dec_total else 0
    absolute_delta = sep_share - dec_share
    if absolute_delta <= 0:
        return None

    decline_percentage = absolute_delta / sep_share
    ranking_score = absolute_delta * decline_percentage

    monthly_mentions = {
        month: len(monthly_post_sets[month])
        for month in all_months
    }
    monthly_shares = {
        month: (monthly_mentions[month] / monthly_totals[month] if monthly_totals[month] else 0)
        for month in all_months
    }

    group_id = _make_group_id(representative_topic, members)
    confidence = _group_confidence(member_evidence)
    merge_method = "single_signal" if len(members) == 1 else "post_overlap"

    return {
        "rank": 0,
        "topic": group_id,
        "group_id": group_id,
        "label": _title_label(representative_topic),
        "representative_topic": representative_topic,
        "member_topics": members,
        "sep_mentions": sep_count,
        "dec_mentions": dec_count,
        "sep_share": round(sep_share, 6),
        "dec_share": round(dec_share, 6),
        "absolute_delta": round(absolute_delta, 6),
        "decline_percentage": round(decline_percentage, 4),
        "ranking_score": round(ranking_score, 8),
        "monthly_mentions": monthly_mentions,
        "monthly_shares": {k: round(v, 6) for k, v in monthly_shares.items()},
        "channels": _compute_group_channel_drops(members, post_index, channel_monthly_totals),
        "representative_posts": _select_representative_posts(members, post_index),
        "consolidation": {
            "member_count": len(members),
            "merge_method": merge_method,
            "confidence": round(confidence, 3),
            "evidence_summary": _evidence_summary(representative_topic, member_evidence),
            "members": member_evidence,
        },
        "raw_signal_ranks": {
            topic: raw_by_topic[topic].ranking_score
            for topic in members
            if topic in raw_by_topic
        },
    }


def _compute_group_channel_drops(
    members: list[str],
    post_index: TopicPostIndex,
    channel_monthly_totals: dict[str, dict[str, int]],
    top_n_channels: int = 10,
) -> list[dict[str, Any]]:
    channel_month_sets: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for topic in members:
        for channel, month_data in post_index.topic_channel_month_posts.get(topic, {}).items():
            for month, post_ids in month_data.items():
                channel_month_sets[channel][month].update(post_ids)

    channel_scores = []
    for channel, month_sets in channel_month_sets.items():
        sep_count = len(month_sets.get("2025-09", set()))
        dec_count = len(month_sets.get("2025-12", set()))
        if sep_count < 5:
            continue

        sep_total = channel_monthly_totals.get(channel, {}).get("2025-09", 0)
        dec_total = channel_monthly_totals.get(channel, {}).get("2025-12", 0)
        if sep_total == 0:
            continue

        sep_share = sep_count / sep_total
        dec_share = dec_count / dec_total if dec_total else 0
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

    channel_scores.sort(
        key=lambda row: (row["sep_mentions"] - row["dec_mentions"], row["decline_percentage"]),
        reverse=True,
    )
    return channel_scores[:top_n_channels]


def _select_representative_posts(
    members: list[str],
    post_index: TopicPostIndex,
    max_posts: int = 5,
) -> list[dict[str, str]]:
    sep_post_ids: set[str] = set()
    for topic in members:
        sep_post_ids.update(post_index.topic_month_posts.get(topic, {}).get("2025-09", set()))

    posts = [
        post_index.post_info[post_id]
        for post_id in sep_post_ids
        if post_id in post_index.post_info
    ]
    posts.sort(key=lambda post: post["published_at"])

    out = []
    for post in posts[:max_posts]:
        content = post["content"]
        out.append({
            "id": post["id"],
            "published_at": post["published_at"],
            "content": content[:500] + "..." if len(content) > 500 else content,
            "channel": post["channel"],
        })
    return out


def _evaluate_pair(
    topic_a: str,
    topic_b: str,
    post_index: TopicPostIndex,
    monthly_totals: dict[str, int],
    ai_labels: Optional[dict[str, dict[str, str]]] = None,
    candidate_topics: Optional[set[str]] = None,
) -> MergeEvidence:
    posts_a = _all_posts(topic_a, post_index)
    posts_b = _all_posts(topic_b, post_index)
    intersection = posts_a.intersection(posts_b)
    union = posts_a.union(posts_b)

    if not posts_a or not posts_b or not union:
        return _no_merge("missing post overlap")

    coverage_a = len(intersection) / len(posts_a)
    coverage_b = len(intersection) / len(posts_b)
    jaccard = len(intersection) / len(union)
    pattern = _monthly_pattern_similarity(topic_a, topic_b, post_index, monthly_totals)
    pair_type = _pair_type(topic_a, topic_b, ai_labels, candidate_topics)

    merge = False
    method = pair_type

    if len(intersection) >= MIN_INTERSECTION_POSTS and pattern >= MIN_PATTERN_SIMILARITY:
        min_coverage = min(coverage_a, coverage_b)
        if pair_type == "broad_narrow":
            merge = (
                jaccard >= BROAD_NARROW_MIN_JACCARD
                and min_coverage >= BROAD_NARROW_MIN_DIRECTIONAL_COVERAGE
                and _size_ratio(posts_a, posts_b) >= BROAD_NARROW_MIN_TOTAL_SIZE_RATIO
                and _sep_size_ratio(topic_a, topic_b, post_index) >= BROAD_NARROW_MIN_SEP_SIZE_RATIO
            )
        elif pair_type in {"same_words", "reversed_bigram", "same_ai_label"}:
            merge = (
                jaccard >= ALIAS_MIN_JACCARD
                and min_coverage >= ALIAS_MIN_DIRECTIONAL_COVERAGE
            )
        elif pair_type == "compound_unigrams":
            merge = (
                jaccard >= GENERAL_MIN_JACCARD
                and min_coverage >= GENERAL_MIN_DIRECTIONAL_COVERAGE
            )
        else:
            merge = (
                jaccard >= GENERAL_MIN_JACCARD
                and min_coverage >= GENERAL_MIN_DIRECTIONAL_COVERAGE
            )

    confidence = _confidence(jaccard, coverage_a, coverage_b, pattern)
    summary = (
        f"{len(intersection)} shared posts; Jaccard {jaccard:.2f}; "
        f"directional coverage {coverage_a:.2f}/{coverage_b:.2f}; "
        f"monthly pattern {pattern:.2f}"
    )
    return MergeEvidence(
        merge=merge,
        method=method,
        confidence=confidence if merge else 0,
        intersection_posts=len(intersection),
        jaccard=jaccard,
        coverage_a_to_b=coverage_a,
        coverage_b_to_a=coverage_b,
        pattern_similarity=pattern,
        summary=summary,
    )


def _no_merge(summary: str) -> MergeEvidence:
    return MergeEvidence(False, "none", 0, 0, 0, 0, 0, 0, summary)


def _all_posts(topic: str, post_index: TopicPostIndex) -> set[str]:
    posts: set[str] = set()
    for post_ids in post_index.topic_month_posts.get(topic, {}).values():
        posts.update(post_ids)
    return posts


def _is_plausible_pair(
    topic_a: str,
    topic_b: str,
    candidate_topics: set[str],
    ai_labels: Optional[dict[str, dict[str, str]]] = None,
) -> bool:
    return _pair_type(topic_a, topic_b, ai_labels, candidate_topics) != "unrelated"


def _pair_type(
    topic_a: str,
    topic_b: str,
    ai_labels: Optional[dict[str, dict[str, str]]] = None,
    candidate_topics: Optional[set[str]] = None,
) -> str:
    words_a = topic_a.split()
    words_b = topic_b.split()
    set_a = set(words_a)
    set_b = set(words_b)

    if sorted(words_a) == sorted(words_b):
        return "same_words"
    if len(words_a) == 2 and words_a == list(reversed(words_b)):
        return "reversed_bigram"
    if set_a < set_b or set_b < set_a:
        return "broad_narrow"
    if topic_a in topic_b or topic_b in topic_a:
        return "broad_narrow"
    if len(words_a) == 1 and len(words_b) == 1 and candidate_topics:
        if any(set([topic_a, topic_b]).issubset(set(candidate.split())) for candidate in candidate_topics):
            return "compound_unigrams"
    if ai_labels and _label_key(topic_a, ai_labels) and _label_key(topic_a, ai_labels) == _label_key(topic_b, ai_labels):
        return "same_ai_label"
    return "unrelated"


def _label_key(topic: str, ai_labels: dict[str, dict[str, str]]) -> str:
    entry = ai_labels.get(topic) or {}
    label = entry.get("short_label") or entry.get("label") or ""
    key = re.sub(r"\s+", " ", label.strip().lower())
    if key in GENERIC_AI_LABEL_HINTS:
        return ""
    return key


def _monthly_pattern_similarity(
    topic_a: str,
    topic_b: str,
    post_index: TopicPostIndex,
    monthly_totals: dict[str, int],
) -> float:
    months = sorted(monthly_totals.keys())
    vec_a = [
        len(post_index.topic_month_posts.get(topic_a, {}).get(month, set())) / monthly_totals[month]
        if monthly_totals[month] else 0
        for month in months
    ]
    vec_b = [
        len(post_index.topic_month_posts.get(topic_b, {}).get(month, set())) / monthly_totals[month]
        if monthly_totals[month] else 0
        for month in months
    ]
    return _cosine_similarity(vec_a, vec_b)


def _cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0
    return dot / (norm_a * norm_b)


def _size_ratio(posts_a: set[str], posts_b: set[str]) -> float:
    larger = max(len(posts_a), len(posts_b))
    smaller = min(len(posts_a), len(posts_b))
    return smaller / larger if larger else 0


def _sep_size_ratio(topic_a: str, topic_b: str, post_index: TopicPostIndex) -> float:
    sep_a = post_index.topic_month_posts.get(topic_a, {}).get("2025-09", set())
    sep_b = post_index.topic_month_posts.get(topic_b, {}).get("2025-09", set())
    larger = max(len(sep_a), len(sep_b))
    smaller = min(len(sep_a), len(sep_b))
    return smaller / larger if larger else 0


def _confidence(jaccard: float, coverage_a: float, coverage_b: float, pattern: float) -> float:
    return min(0.99, (jaccard + coverage_a + coverage_b + pattern) / 4)


def _group_confidence(member_evidence: list[dict[str, Any]]) -> float:
    if not member_evidence:
        return 1.0
    return sum(row["confidence"] for row in member_evidence) / len(member_evidence)


def _evidence_summary(representative_topic: str, member_evidence: list[dict[str, Any]]) -> str:
    if not member_evidence:
        return "Single lexical signal; no deterministic merge applied."
    merged = ", ".join(row["topic"] for row in member_evidence)
    return f"Grouped {representative_topic} with {merged} using reciprocal post overlap."


def _make_group_id(representative_topic: str, members: list[str]) -> str:
    if len(members) == 1:
        return representative_topic
    digest = hashlib.sha1("|".join(sorted(members)).encode("utf-8")).hexdigest()[:8]
    return f"{representative_topic}::{digest}"


def _title_label(topic: str) -> str:
    return " ".join(word.capitalize() for word in topic.split())
