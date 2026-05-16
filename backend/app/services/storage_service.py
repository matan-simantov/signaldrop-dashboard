"""
Artifact storage abstraction. Reads precomputed JSON artifacts from local disk or S3.
The backend never processes raw data — it only serves precomputed insights.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import boto3
from botocore.exceptions import ClientError

from ..config import settings


class StorageService:
    """Reads JSON artifacts from local filesystem or S3."""

    def __init__(self):
        self._cache: dict[str, Any] = {}
        if settings.ARTIFACTS_SOURCE == "s3":
            self._s3 = boto3.client("s3", region_name=settings.AWS_REGION)

    def get_artifact(self, name: str) -> Optional[Any]:
        """Load a named artifact (e.g., 'trends', 'overview'). Results are cached."""
        if name in self._cache:
            return self._cache[name]

        data = self._load(name)
        if data is not None:
            self._cache[name] = data
        return data

    def _load(self, name: str) -> Optional[Any]:
        if settings.ARTIFACTS_SOURCE == "s3":
            return self._load_from_s3(name)
        return self._load_from_local(name)

    def _load_from_local(self, name: str) -> Optional[Any]:
        path = settings.ARTIFACTS_LOCAL_PATH / f"{name}.json"
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_from_s3(self, name: str) -> Optional[Any]:
        prefix = settings.ARTIFACTS_PREFIX
        # Ensure trailing slash so it joins cleanly
        if prefix and not prefix.endswith("/"):
            prefix = prefix + "/"
        key = f"{prefix}{name}.json"
        try:
            response = self._s3.get_object(Bucket=settings.S3_BUCKET, Key=key)
            return json.loads(response["Body"].read().decode("utf-8"))
        except ClientError:
            return None


storage_service = StorageService()
