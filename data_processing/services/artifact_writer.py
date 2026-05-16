"""
Writes processed trend data as JSON artifacts that the backend serves.
Artifacts are self-contained — the live API never touches the raw CSV.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_artifact(output_dir: Path, name: str, data: Any) -> Path:
    """Write a JSON artifact to the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    return path


def write_all_artifacts(
    output_dir: Path,
    overview: dict,
    trends: list[dict],
    trend_timeseries: dict,
    channel_breakdown: dict,
    representative_posts: dict,
    methodology: dict,
    consolidated_trends: list[dict] | None = None,
) -> dict[str, Path]:
    """Write all processed artifacts. Returns map of artifact name to file path."""
    paths = {}
    artifacts = {
        "overview": overview,
        "trends": trends,
        "trend_timeseries": trend_timeseries,
        "channel_breakdown": channel_breakdown,
        "representative_posts": representative_posts,
        "methodology": methodology,
    }
    if consolidated_trends is not None:
        artifacts["consolidated_trends"] = consolidated_trends
    for name, data in artifacts.items():
        paths[name] = write_artifact(output_dir, name, data)
    return paths
