"""
Business logic for serving trend data from precomputed artifacts.
"""

from __future__ import annotations

from typing import Any, Optional

from .storage_service import storage_service


class TrendService:
    def get_overview(self) -> Optional[dict]:
        return storage_service.get_artifact("overview")

    def get_trends(self) -> Optional[list[dict]]:
        return storage_service.get_artifact("trends")

    def get_trend_detail(self, topic: str) -> Optional[dict]:
        """Assemble a detailed view for a specific topic."""
        trends = storage_service.get_artifact("trends")
        timeseries = storage_service.get_artifact("trend_timeseries")
        channels = storage_service.get_artifact("channel_breakdown")
        posts = storage_service.get_artifact("representative_posts")

        if not trends or not timeseries:
            return None

        trend_entry = next((t for t in trends if t["topic"] == topic), None)
        if not trend_entry:
            return None

        return {
            "trend": trend_entry,
            "timeseries": timeseries.get(topic),
            "channels": channels.get(topic, []) if channels else [],
            "representative_posts": posts.get(topic, []) if posts else [],
        }

    def get_channels(self, topic: Optional[str] = None) -> Optional[Any]:
        breakdown = storage_service.get_artifact("channel_breakdown")
        if not breakdown:
            return None
        if topic:
            return breakdown.get(topic, [])
        return breakdown

    def get_methodology(self) -> Optional[dict]:
        return storage_service.get_artifact("methodology")

    def get_ai_labels(self) -> dict:
        """Return AI labels artifact, or empty dict if not generated."""
        labels = storage_service.get_artifact("ai_labels")
        return labels if labels else {}


trend_service = TrendService()
