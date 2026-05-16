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
        return self._get_preferred_trends()

    def get_trend_detail(self, topic: str) -> Optional[dict]:
        """Assemble a detailed view for a specific topic."""
        consolidated = storage_service.get_artifact("consolidated_trends")
        if consolidated:
            trend_entry = self._find_consolidated_trend(consolidated, topic)
            if not trend_entry:
                return None
            return {
                "trend": trend_entry,
                "timeseries": {
                    "monthly_shares": trend_entry.get("monthly_shares", {}),
                    "monthly_mentions": trend_entry.get("monthly_mentions", {}),
                },
                "channels": trend_entry.get("channels", []),
                "representative_posts": trend_entry.get("representative_posts", []),
            }

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
        consolidated = storage_service.get_artifact("consolidated_trends")
        if consolidated:
            if topic:
                trend_entry = self._find_consolidated_trend(consolidated, topic)
                return trend_entry.get("channels", []) if trend_entry else []
            return {
                trend["topic"]: trend.get("channels", [])
                for trend in consolidated
            }

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

    def get_ai_insights(self) -> dict:
        """Return AI-generated key findings artifact, or empty dict if not generated."""
        insights = storage_service.get_artifact("ai_insights")
        return insights if insights else {}

    def _get_preferred_trends(self) -> Optional[list[dict]]:
        consolidated = storage_service.get_artifact("consolidated_trends")
        if consolidated:
            return consolidated
        return storage_service.get_artifact("trends")

    def _find_consolidated_trend(self, trends: list[dict], topic: str) -> Optional[dict]:
        return next(
            (
                trend for trend in trends
                if topic in {
                    trend.get("topic"),
                    trend.get("group_id"),
                    trend.get("representative_topic"),
                    *trend.get("member_topics", []),
                }
            ),
            None,
        )


trend_service = TrendService()
