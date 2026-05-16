"""
Optional: generate AI labels for the top trends.

Usage:
  export ANTHROPIC_API_KEY=...
  python -m data_processing.scripts.generate_ai_labels --artifacts ./artifacts

If ANTHROPIC_API_KEY is missing, this script prints a message and exits cleanly.
The rest of the project works fine without AI labels.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_processing.services.topic_labeling_service import run


def main():
    parser = argparse.ArgumentParser(description="Generate AI labels for top trends")
    parser.add_argument("--artifacts", default="./artifacts", help="Artifacts directory")
    args = parser.parse_args()

    success = run(Path(args.artifacts))
    sys.exit(0 if success else 0)  # exit 0 even on skip — this is optional


if __name__ == "__main__":
    main()
