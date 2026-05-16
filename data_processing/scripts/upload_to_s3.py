"""
Upload processed artifacts to S3.
Usage: python -m data_processing.scripts.upload_to_s3 --artifacts ./artifacts
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import boto3


def main():
    parser = argparse.ArgumentParser(description="Upload artifacts to S3")
    parser.add_argument("--artifacts", default="./artifacts", help="Local artifacts directory")
    args = parser.parse_args()

    bucket = os.getenv("S3_BUCKET", "signaldrop-data-matan-2026")
    region = os.getenv("AWS_REGION", "eu-west-2")

    s3 = boto3.client("s3", region_name=region)
    artifacts_dir = Path(args.artifacts)

    for json_file in artifacts_dir.glob("*.json"):
        key = f"processed/{json_file.name}"
        print(f"  Uploading {json_file.name} → s3://{bucket}/{key}")
        s3.upload_file(
            str(json_file), bucket, key,
            ExtraArgs={"ContentType": "application/json"},
        )

    print(f"\nDone! {len(list(artifacts_dir.glob('*.json')))} artifacts uploaded.")


if __name__ == "__main__":
    main()
