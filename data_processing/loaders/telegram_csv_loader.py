"""
Loader for the Telegram CSV export format.
Expected columns: id, dt_published, translated_content, channel_name, channel_id
"""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .base_loader import BaseLoader, NormalizedPost


class TelegramCsvLoader(BaseLoader):
    def __init__(self, csv_path: str | Path):
        self.csv_path = Path(csv_path)
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV not found: {self.csv_path}")

    @property
    def source_type(self) -> str:
        return "telegram"

    def load(self) -> Iterator[NormalizedPost]:
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                yield NormalizedPost(
                    id=row["id"],
                    published_at=datetime.strptime(row["dt_published"], "%Y-%m-%d %H:%M:%S"),
                    content=row["translated_content"],
                    source_name=row["channel_name"],
                    source_id=str(row["channel_id"]),
                    source_type=self.source_type,
                )
