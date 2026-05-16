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


SYSTEM_PROMPT = """You are an analyst summarizing declining conversation trends from public Telegram channels covering Israeli news and politics, September–December 2025.

For each trend keyword, output a JSON object with:
  - "label": a short, human-readable headline (max 6 words) capturing what the keyword likely refers to
  - "category": one of [Geopolitics, Conflict, Diplomacy, Domestic Politics, Media/Platforms, Society, Other]
  - "explanation": one sentence (max 25 words) explaining what the topic represented in this dataset

Be neutral, factual, and concise. If the keyword is ambiguous, say so.
Output ONLY valid JSON, no commentary."""


def build_user_prompt(trends: list[dict], representative_posts: dict) -> str:
    """Pack top trends and a couple of example posts each into a single compact prompt."""
    lines = ["Label the following declining trends:\n"]
    for t in trends:
        topic = t["topic"]
        examples = representative_posts.get(topic, [])[:2]
        example_text = ""
        if examples:
            snippets = [ex["content"][:200].replace("\n", " ") for ex in examples]
            example_text = "\n    Examples: " + " | ".join(snippets)
        lines.append(
            f"- Keyword: \"{topic}\" "
            f"(Sep mentions: {t['sep_mentions']}, Dec mentions: {t['dec_mentions']}, "
            f"decline: {int(t['decline_percentage'] * 100)}%)"
            f"{example_text}"
        )
    lines.append(
        '\nRespond with a JSON object mapping each keyword to '
        '{"label", "category", "explanation"}.'
    )
    return "\n".join(lines)


DEFAULT_MODEL = "claude-sonnet-4-6"


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


def run(artifacts_dir: Path) -> bool:
    """
    Read top trends + examples from artifacts_dir, generate AI labels,
    write ai_labels.json. Returns True on success, False if skipped/failed.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ai-labeling] Skipping: ANTHROPIC_API_KEY not set. The deterministic pipeline already produced complete results.")
        return False

    trends_path = artifacts_dir / "trends.json"
    posts_path = artifacts_dir / "representative_posts.json"

    if not trends_path.exists() or not posts_path.exists():
        print(f"[ai-labeling] Missing required artifacts in {artifacts_dir}. Run ingest_and_compute first.")
        return False

    with open(trends_path) as f:
        trends = json.load(f)
    with open(posts_path) as f:
        representative_posts = json.load(f)

    print(f"[ai-labeling] Generating labels for {len(trends)} trends via Anthropic API...")
    labels = generate_labels(trends, representative_posts, api_key)

    if labels is None:
        print("[ai-labeling] Failed to generate labels. Falling back to deterministic topic names.")
        return False

    output_path = artifacts_dir / "ai_labels.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(labels, f, indent=2, ensure_ascii=False)

    print(f"[ai-labeling] Wrote {len(labels)} labels to {output_path}")
    return True
