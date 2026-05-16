"""
Display-quality scoring for consolidated trend groups.

This layer does not change analytical grouping, counts, or ranking. It only
marks generic or duplicate-looking signals so the dashboard can prefer
topic-like groups in the main list while the backend still serves the full
artifact.
"""

from __future__ import annotations

from typing import Any


WEAK_STANDALONE_TERMS = frozenset({
    "city",
    "september",
    "platforms",
    "speech",
    "today",
    "people",
    "report",
    "video",
    "news",
    "rosh",
})

KEEP_STANDALONE_TERMS = frozenset({
    "hostages",
    "qatar",
    "gaza",
    "hamas",
    "houthi",
    "trump",
    "kirk",
    "tiktok",
    "instagram",
    "yemen",
    "doha",
    "zini",
})


def apply_display_quality(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Annotate groups with deterministic display quality metadata."""
    more_specific_phrases = _phrase_index(groups)
    duplicate_token_keep = _best_by_token_set(groups)

    for group in groups:
        rep = group.get("representative_topic", group.get("topic", ""))
        members = group.get("member_topics", [rep])
        notes: list[str] = []
        is_displayable = True
        reason = ""
        score = 1.0

        token_key = _token_key(rep)
        if token_key in duplicate_token_keep and duplicate_token_keep[token_key] != group.get("group_id", group.get("topic")):
            is_displayable = False
            reason = "duplicate_reversed_or_token_set"
            score = 0.35
            notes.append(
                f"Hidden from main list because a stronger group uses the same token set: {token_key}."
            )

        if is_displayable and rep in WEAK_STANDALONE_TERMS and rep not in KEEP_STANDALONE_TERMS:
            is_displayable = False
            reason = "generic_weak_standalone_term"
            score = 0.25
            notes.append(f"'{rep}' is a weak standalone display term.")

        if is_displayable and len(rep.split()) == 1 and rep not in KEEP_STANDALONE_TERMS:
            phrases = more_specific_phrases.get(rep, [])
            if phrases and rep in WEAK_STANDALONE_TERMS:
                is_displayable = False
                reason = "partial_phrase_fragment"
                score = 0.3
                notes.append(
                    f"'{rep}' appears to be a fragment of more specific signals: {', '.join(phrases[:3])}."
                )

        if is_displayable:
            notes.append("Kept visible: no conservative genericness rule matched.")

        group["display_quality_score"] = score
        group["is_displayable"] = is_displayable
        group["display_exclusion_reason"] = reason
        group["quality_notes"] = notes

    return groups


def _phrase_index(groups: list[dict[str, Any]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    for group in groups:
        rep = group.get("representative_topic", "")
        words = rep.split()
        if len(words) <= 1:
            continue
        for word in words:
            index.setdefault(word, []).append(rep)
    return index


def _best_by_token_set(groups: list[dict[str, Any]]) -> dict[str, str]:
    buckets: dict[str, list[dict[str, Any]]] = {}
    for group in groups:
        rep = group.get("representative_topic", "")
        if len(rep.split()) <= 1:
            continue
        buckets.setdefault(_token_key(rep), []).append(group)

    keep: dict[str, str] = {}
    for key, bucket in buckets.items():
        if len(bucket) <= 1:
            continue
        best = sorted(
            bucket,
            key=lambda g: (
                g.get("ranking_score", 0),
                len(g.get("representative_topic", "")),
            ),
            reverse=True,
        )[0]
        keep[key] = best.get("group_id", best.get("topic"))
    return keep


def _token_key(topic: str) -> str:
    return " ".join(sorted(topic.split()))
