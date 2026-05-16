"""
Backend configuration. All values come from environment variables with sensible defaults.
"""

from __future__ import annotations

import os
from pathlib import Path


class Settings:
    AWS_REGION: str = os.getenv("AWS_REGION", "eu-west-2")
    S3_BUCKET: str = os.getenv("S3_BUCKET", "signaldrop-data-matan-2026")

    # "local" reads from disk, "s3" reads from S3 <bucket>/<prefix>
    ARTIFACTS_SOURCE: str = os.getenv("ARTIFACTS_SOURCE", "local")
    ARTIFACTS_LOCAL_PATH: Path = Path(os.getenv("ARTIFACTS_LOCAL_PATH", "./artifacts"))
    ARTIFACTS_PREFIX: str = os.getenv("ARTIFACTS_PREFIX", "processed/")

    CORS_ORIGINS: list = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
        if origin.strip()
    ]


settings = Settings()
