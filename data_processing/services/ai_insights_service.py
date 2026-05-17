"""
Optional AI summaries for deterministic trend outputs.

The LLM receives only precomputed trend data and may produce wording only. It
does not calculate counts, shares, rankings, decline metrics, or groupings.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from data_processing.services.topic_labeling_service import DEFAULT_MODEL


SYSTEM_PROMPT = """You summarize deterministic declining trend outputs for a small public Telegram dashboard.

Return ONLY valid JSON with:
{
  "headline": "short neutral headline, max 8 words",
  "findings": [
    {"title": "short label, max 6 words", "detail": "one short factual sentence, MAX 18 words"},
    {"title": "short label, max 6 words", "detail": "one short factual sentence, MAX 18 words"},
    {"title": "short label, max 6 words", "detail": "one short factual sentence, MAX 18 words"}
  ],
  "caveat": "optional methodology note, max 20 words"
}

Strict rules:
- Use only the deterministic facts provided by the user.
- Do not invent facts, causes, events, implications, or metrics.
- Do not calculate or derive new counts, shares, percentages, rankings, or decline metrics.
- If you mention rank, say "ranked by deterministic scoring" rather than "ranked by share decline".
- If you include a number, copy it exactly from the supplied facts.
- Do not decide topic grouping or scoring.
- Use neutral, conservative language. Avoid the phrases "true discourse", "real-world decline", "original source", "definitive opinion".
- Prefer the phrases "observed Telegram posts", "deduplicated topic signals", "canonical posts" when natural.
- Focus only on declining topic signals across observed Telegram posts.
- Each "detail" string MUST be a single sentence of at most 18 words. Be terse; cut filler words.
- Prefer executive-summary themes over listing individual ranks."""


NUMBER_PATTERN = re.compile(r"\d[\d,]*(?:\.\d+)?%?")


def build_insights_prompt(trends: list[dict], labels: dict[str, dict[str, str]]) -> tuple[str, set[str]]:
    """Build a compact prompt and return the set of numeric strings AI may copy."""
    facts = []
    display_trends = [trend for trend in trends if trend.get("is_displayable", True)]
    merged_groups = [trend for trend in trends if len(trend.get("member_topics", [])) > 1]
    hidden_groups = [trend for trend in trends if not trend.get("is_displayable", True)]

    for trend in display_trends[:10]:
        topic = trend["topic"]
        label_entry = labels.get(topic, {})
        label = label_entry.get("short_label") or label_entry.get("label") or trend.get("label") or trend.get("representative_topic", topic)
        channels = trend.get("channels", [])[:3]
        channel_text = ", ".join(
            f"{ch['channel']} ({ch['sep_mentions']} to {ch['dec_mentions']} mentions)"
            for ch in channels
        )
        member_topics = trend.get("member_topics", [trend.get("representative_topic", topic)])
        facts.append({
            "rank": trend.get("rank"),
            "trend_id": topic,
            "label": label,
            "member_signals": member_topics,
            "sep_mentions": trend["sep_mentions"],
            "sep_mentions_formatted": f"{trend['sep_mentions']:,}",
            "dec_mentions": trend["dec_mentions"],
            "dec_mentions_formatted": f"{trend['dec_mentions']:,}",
            "sep_share": f"{trend['sep_share'] * 100:.2f}%",
            "dec_share": f"{trend['dec_share'] * 100:.2f}%",
            "decline_percentage": f"{round(trend['decline_percentage'] * 100)}%",
            "ranking_score": trend["ranking_score"],
            "top_declining_channels": channel_text,
        })

    payload = {
        "period": "September to December 2025",
        "consolidation_summary": {
            "total_groups": len(trends),
            "displayable_groups": len(display_trends),
            "hidden_from_main_display": len(hidden_groups),
            "merged_groups": [
                {
                    "label": (labels.get(trend["topic"], {}).get("short_label") or trend.get("label")),
                    "member_signals": trend.get("member_topics", []),
                }
                for trend in merged_groups
            ],
        },
        "methodology_constraints": [
            "Trends are ranked by deterministic normalized September-to-December share decline.",
            "Consolidated trend metrics use unique post IDs, not summed member counts.",
            "The display quality pass can hide generic signals from the main list without deleting them from artifacts.",
            "AI may summarize only these deterministic outputs.",
        ],
        "facts": facts,
    }
    prompt = (
        "Write one short headline and exactly three executive-summary key findings from these deterministic facts. "
        "Use the supplied labels when helpful. Do not add numbers unless copied exactly. "
        "If you mention rank, describe it as deterministic scoring, not as share decline alone. "
        "Each finding 'detail' MUST be a single sentence and at most 18 words — be terse, cut adjectives. "
        "Aim for these themes if supported by the facts: event-driven topics faded fastest; "
        "broad conflict topics declined less sharply but remained central; deduplication and consolidation "
        "reduced amplification and duplicate lexical signals without changing deterministic metrics.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )
    allowed_numbers = set(NUMBER_PATTERN.findall(prompt))
    allowed_numbers.update(number.rstrip(",") for number in list(allowed_numbers))
    return prompt, allowed_numbers


def generate_ai_insights(
    trends: list[dict],
    labels: dict[str, dict[str, str]],
    api_key: str,
    model: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    try:
        from anthropic import Anthropic
    except ImportError:
        print("[ai-insights] anthropic package not installed. Run: pip install anthropic")
        return None

    prompt, allowed_numbers = build_insights_prompt(trends, labels)
    resolved_model = model or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL
    client = Anthropic(api_key=api_key)
    print(f"[ai-insights] Using model: {resolved_model}")

    try:
        response = client.messages.create(
            model=resolved_model,
            max_tokens=1600,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"[ai-insights] API call failed: {e}")
        return None

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        insights = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[ai-insights] Failed to parse LLM JSON output: {e}")
        print(f"[ai-insights] Raw output:\n{text[:500]}")
        return None

    if not validate_ai_insights(insights, allowed_numbers):
        # Surface which numeric tokens the LLM introduced that are not in the prompt.
        offending = sorted(
            set(NUMBER_PATTERN.findall(json.dumps(insights, ensure_ascii=False)))
            - allowed_numbers
        )
        print(
            "[ai-insights] Validation failed: output contains numbers not in the prompt: "
            f"{offending}. Falling back to deterministic key findings."
        )
        return None
    return insights


def validate_ai_insights(insights: Any, allowed_numbers: set[str]) -> bool:
    if not isinstance(insights, dict):
        return False
    if not isinstance(insights.get("headline"), str) or not insights["headline"].strip():
        return False
    findings = insights.get("findings")
    if not isinstance(findings, list) or len(findings) != 3:
        return False
    for finding in findings:
        if not isinstance(finding, dict):
            return False
        if not isinstance(finding.get("title"), str) or not finding["title"].strip():
            return False
        if not isinstance(finding.get("detail"), str) or not finding["detail"].strip():
            return False

    output_numbers = set(NUMBER_PATTERN.findall(json.dumps(insights, ensure_ascii=False)))
    return output_numbers.issubset(allowed_numbers)


def run(artifacts_dir: Path) -> bool:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ai-insights] Skipping: ANTHROPIC_API_KEY not set. Deterministic key findings remain available.")
        return False

    consolidated_path = artifacts_dir / "consolidated_trends.json"
    trends_path = consolidated_path if consolidated_path.exists() else artifacts_dir / "trends.json"
    labels_path = artifacts_dir / "ai_labels.json"

    if not trends_path.exists():
        print(f"[ai-insights] Missing trend artifacts in {artifacts_dir}. Run ingest_and_compute first.")
        return False

    with open(trends_path, "r", encoding="utf-8") as f:
        trends = json.load(f)

    labels = {}
    if labels_path.exists():
        with open(labels_path, "r", encoding="utf-8") as f:
            labels = json.load(f)

    source = "consolidated_trends.json" if consolidated_path.exists() else "trends.json"
    print(f"[ai-insights] Generating key findings from {source}...")
    insights = generate_ai_insights(trends, labels, api_key)
    if insights is None:
        return False

    output_path = artifacts_dir / "ai_insights.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(insights, f, indent=2, ensure_ascii=False)

    print(f"[ai-insights] Wrote AI key findings to {output_path}")
    return True
