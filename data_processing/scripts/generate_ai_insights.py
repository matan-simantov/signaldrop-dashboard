"""
Optional: generate AI key findings from deterministic artifacts.

Usage:
  export ANTHROPIC_API_KEY=...
  python -m data_processing.scripts.generate_ai_insights --artifacts ./artifacts

If ANTHROPIC_API_KEY is missing, this script prints a message and exits cleanly.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_processing.services.ai_insights_service import run


def main():
    parser = argparse.ArgumentParser(description="Generate AI key findings")
    parser.add_argument("--artifacts", default="./artifacts", help="Artifacts directory")
    args = parser.parse_args()

    run(Path(args.artifacts))
    sys.exit(0)


if __name__ == "__main__":
    main()
