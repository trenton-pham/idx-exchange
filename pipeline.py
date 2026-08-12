"""Run the existing CRMLS data-cleaning scripts as one pipeline."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent

CORE_STAGES = [
    ("Combine monthly data", "process.py"),
    ("Validate and filter data", "validation.py"),
    ("Add mortgage rates", "mortgage_fetch.py"),
    ("Clean data", "clean.py"),
    ("Engineer features", "feature_engineer.py"),
    ("Filter outliers", "outlier.py"),
]

REPORT_STAGE = ("Generate statistics and charts", "distribution.py")

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run all existing CRMLS cleaning scripts in order."
    )
    parser.add_argument(
        "--with-reports",
        action="store_true",
        help="also run distribution.py to regenerate statistics and charts",
    )
    return parser.parse_args()


def get_stages(with_reports: bool) -> list[tuple[str, str]]:
    stages = CORE_STAGES.copy()
    if with_reports:
        stages.insert(1, REPORT_STAGE)
    return stages


def run_pipeline(stages: list[tuple[str, str]]) -> int:
    pipeline_started = time.perf_counter()

    for position, (description, script_name) in enumerate(stages, start=1):
        print(
            f"\n[{position}/{len(stages)}] {description} ({script_name})",
            flush=True,
        )
        stage_started = time.perf_counter()

        subprocess.run(
            [sys.executable, str(PROJECT_DIR / script_name)],
            cwd=PROJECT_DIR,
            check=True,
        )

        elapsed = time.perf_counter() - stage_started
        print(f"Completed {script_name} in {elapsed:.1f} seconds.", flush=True)

    total_elapsed = time.perf_counter() - pipeline_started
    print(f"\nPipeline completed successfully in {total_elapsed:.1f} seconds.")
    return 0

def main() -> int:
    args = parse_args()
    return run_pipeline(get_stages(args.with_reports))

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nPipeline cancelled.", file=sys.stderr)
        raise SystemExit(130)