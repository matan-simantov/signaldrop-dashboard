"""
Optional AI labeling layer.

This service is intentionally separate from the deterministic pipeline.
It reads the top trends (already scored) and produces human-readable labels,
categories, and short explanations as a separate artifact: ai_labels.json.

Design principles:
- Deterministic scoring is the source of truth. AI only adds presentation.
- Skips gracefully when ANTHROPIC_API_KEY is missing — the app must work without it.
- Compact prompts: we send only the top trends' summaries, never the full CSV.
- Run once during preprocessing. The live API never calls the LLM.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional


SYSTEM_PROMPT = """You are an analyst labeling declining topic signals detected across observed public Telegram posts covering Israeli news and politics, September–December 2025.

For each trend keyword, output a JSON object with:
  - "short_label": a very short, neutral headline, 3 to 6 words, suitable for a dashboard list. Examples of the desired tone: "Gaza War Coverage", "Qatar–Hamas Coverage", "Hostage Release Talks", "Yemen Missile Threats", "Charlie Kirk Coverage". No trailing punctuation.
  - "label": same as short_label OR a slightly longer (max 8 words) human-readable form if helpful. May equal short_label.
  - "category": one of [Geopolitics, Conflict, Diplomacy, Domestic Politics, Media/Platforms, Society, Other]
  - "explanation": one neutral sentence (max 25 words) grounded only in the keyword, counts, and example posts provided. No speculation beyond what the data supports.

Strict rules:
- Be neutral, factual, conservative. No dramatic, emotional, or politically loaded framing.
- Prefer broader, grounded descriptions over narrow incident-level labels unless the example posts overwhelmingly support narrowing. For a broad keyword like "gaza" or "qatar", prefer "Gaza War Coverage" or "Qatar–Hamas Coverage", not a single specific event.
- Do NOT use the following words in labels: "incitement", "combat alerts", "assassination" (use "shooting" or "attack" if grounded), "propaganda", "regime", "terrorist", "extremist". Use them in explanations only when directly supported by the example posts.
- Avoid contradicting the methodology: alert templates (rocket-alert location lists) are filtered out of the dataset, so do NOT use "Alerts" / "Combat Alerts" / "Rocket Alerts" as a topic label for broad keywords like "gaza" or "city". Reserve alert-related labels for keywords that clearly are alert-specific (e.g. "alerts activated", "aircraft").
- Keep labels short, neutral, specific, readable. No buzzwords ("ongoing coverage", "broad coverage").
- If the keyword is ambiguous, the short_label should still be specific and grounded in the example posts.
- Output ONLY valid JSON, no commentary, no markdown fences."""


def build_user_prompt(trends: list[dict], representative_posts: dict) -> str:
    """Pack top trends and a couple of example posts each into a single compact prompt."""
    lines = ["Label the following declining trends:\n"]
    for t in trends:
        topic = t["topic"]
        representative_topic = t.get("representative_topic", topic)
        members = t.get("member_topics", [representative_topic])
        examples = representative_posts.get(topic, [])[:2]
        example_text = ""
        if examples:
            snippets = [ex["content"][:200].replace("\n", " ") for ex in examples]
            example_text = "\n    Examples: " + " | ".join(snippets)
        lines.append(
            f"- Trend ID: \"{topic}\" "
            f"(representative signal: \"{representative_topic}\"; "
            f"member signals: {', '.join(members)}) "
            f"(Sep mentions: {t['sep_mentions']}, Dec mentions: {t['dec_mentions']}, "
            f"decline: {int(t['decline_percentage'] * 100)}%)"
            f"{example_text}"
        )
    lines.append(
        '\nRespond with a JSON object mapping each Trend ID to '
        '{"short_label", "label", "category", "explanation"}.'
    )
    return "\n".join(lines)


DEFAULT_MODEL = "claude-sonnet-4-6"


LABEL_OVERRIDES = {
    "tiktok": {
        "short_label": "TikTok Coverage",
        "label": "TikTok Coverage",
        "category": "Media/Platforms",
        "explanation": "Mentions of TikTok declined as part of social-platform references in the analyzed posts.",
    },
    "instagram": {
        "short_label": "Instagram Content Coverage",
        "label": "Instagram Content Coverage",
        "category": "Media/Platforms",
        "explanation": "Mentions of Instagram declined as part of social-platform references in the analyzed posts.",
    },
    "platforms": {
        "short_label": "Social Platform Coverage",
        "label": "Social Platform Coverage",
        "category": "Media/Platforms",
        "explanation": "Mentions of social platforms declined in the analyzed Telegram posts.",
    },
    "facebook whatsapp": {
        "short_label": "Facebook & WhatsApp Mentions",
        "label": "Facebook & WhatsApp Mentions",
        "category": "Media/Platforms",
        "explanation": "Combined Facebook and WhatsApp mentions declined in the analyzed posts.",
    },
    "whatsapp instagram": {
        "short_label": "WhatsApp & Instagram Mentions",
        "label": "WhatsApp & Instagram Mentions",
        "category": "Media/Platforms",
        "explanation": "Combined WhatsApp and Instagram mentions declined in the analyzed posts.",
    },
    "gaza city": {
        "short_label": "Gaza City Operations",
        "label": "Gaza City Operations",
        "category": "Conflict",
        "explanation": "Mentions focused specifically on military activity and strike reports in Gaza City.",
    },
    "city gaza": {
        "short_label": "Gaza City Strike Reports",
        "label": "Gaza City Strike Reports",
        "category": "Conflict",
        "explanation": "Mentions focused on strike reports and casualty updates connected to Gaza City.",
    },
    "rosh": {
        "short_label": "Rosh Hashanah References",
        "label": "Rosh Hashanah References",
        "category": "Society",
        "explanation": "Mentions reference Rosh Hashanah in religious and social contexts.",
    },
}


def generate_labels(
    trends: list[dict],
    representative_posts: dict,
    api_key: str,
    model: Optional[str] = None,
) -> Optional[dict]:
    """Call the Anthropic API to label trends. Returns None on failure."""
    try:
        from anthropic import Anthropic
    except ImportError:
        print("[ai-labeling] anthropic package not installed. Run: pip install anthropic")
        return None

    # Model precedence: explicit arg > ANTHROPIC_MODEL env > DEFAULT_MODEL
    resolved_model = model or os.getenv("ANTHROPIC_MODEL") or DEFAULT_MODEL

    client = Anthropic(api_key=api_key)
    prompt = build_user_prompt(trends, representative_posts)
    print(f"[ai-labeling] Using model: {resolved_model}")

    try:
        response = client.messages.create(
            model=resolved_model,
            max_tokens=4000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception as e:
        print(f"[ai-labeling] API call failed: {e}")
        return None

    text = response.content[0].text.strip()

    # Strip markdown fences if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[ai-labeling] Failed to parse LLM JSON output: {e}")
        print(f"[ai-labeling] Raw output:\n{text[:500]}")
        return None


def apply_label_overrides(labels: dict, trends: list[dict]) -> dict:
    """Apply deterministic label overrides for known duplicate-looking display labels."""
    for trend in trends:
        topic = trend["topic"]
        representative = trend.get("representative_topic", topic)
        override = LABEL_OVERRIDES.get(topic) or LABEL_OVERRIDES.get(representative)
        if override:
            labels[topic] = override
    return labels


def run(artifacts_dir: Path) -> bool:
    """
    Read top trends + examples from artifacts_dir, generate AI labels,
    write ai_labels.json. Returns True on success, False if skipped/failed.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ai-labeling] Skipping: ANTHROPIC_API_KEY not set. The deterministic pipeline already produced complete results.")
        return False

    consolidated_path = artifacts_dir / "consolidated_trends.json"
    trends_path = consolidated_path if consolidated_path.exists() else artifacts_dir / "trends.json"
    posts_path = artifacts_dir / "representative_posts.json"

    if not trends_path.exists():
        print(f"[ai-labeling] Missing required artifacts in {artifacts_dir}. Run ingest_and_compute first.")
        return False

    with open(trends_path) as f:
        trends = json.load(f)

    if consolidated_path.exists():
        representative_posts = {
            trend["topic"]: trend.get("representative_posts", [])
            for trend in trends
        }
        print("[ai-labeling] Using consolidated_trends.json as the labeling source.")
    elif posts_path.exists():
        with open(posts_path) as f:
            representative_posts = json.load(f)
    else:
        representative_posts = {}

    print(f"[ai-labeling] Generating labels for {len(trends)} trends via Anthropic API...")
    labels = generate_labels(trends, representative_posts, api_key)

    if labels is None:
        print("[ai-labeling] Failed to generate labels. Falling back to deterministic topic names.")
        return False

    labels = apply_label_overrides(labels, trends)

    output_path = artifacts_dir / "ai_labels.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2, ensure_ascii=False)

    print(f"[ai-labeling] Wrote {len(labels)} labels to {output_path}")
    return True
