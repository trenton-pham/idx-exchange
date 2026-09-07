"""Run CRMLS extraction and data-cleaning scripts as one pipeline."""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent

CORE_STAGES = [
    ("Combine monthly data", ["process.py"]),
    ("Validate and filter data", ["validation.py"]),
    ("Add mortgage rates", ["mortgage_fetch.py"]),
    ("Clean data", ["clean.py"]),
    ("Engineer features", ["feature_engineer.py"]),
    ("Filter outliers", ["outlier.py"]),
]

REPORT_STAGE = ("Generate statistics and charts", ["distribution.py"])


def month_argument(value: str) -> str:
    try:
        time.strptime(value, "%Y-%m")
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"invalid month {value!r}; expected YYYY-MM"
        ) from error
    if len(value) != 7:
        raise argparse.ArgumentTypeError(
            f"invalid month {value!r}; expected YYYY-MM"
        )
    return value


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Optionally fetch monthly CRMLS data, then run the transformation "
            "scripts in order."
        )
    )
    parser.add_argument(
        "--with-reports",
        action="store_true",
        help="also run distribution.py to regenerate statistics and charts",
    )
    parser.add_argument(
        "--fetch-start",
        type=month_argument,
        help="first month to fetch from Trestle (YYYY-MM); may span multiple years",
    )
    parser.add_argument(
        "--fetch-end",
        type=month_argument,
        help="last month to fetch from Trestle, inclusive (YYYY-MM)",
    )
    parser.add_argument(
        "--force-fetch",
        action="store_true",
        help="replace existing monthly CSVs after successful validation",
    )
    args = parser.parse_args(argv)
    if bool(args.fetch_start) != bool(args.fetch_end):
        parser.error("--fetch-start and --fetch-end must be supplied together")
    if args.fetch_start and args.fetch_end and args.fetch_end < args.fetch_start:
        parser.error("--fetch-end must not be earlier than --fetch-start")
    if args.force_fetch and not args.fetch_start:
        parser.error("--force-fetch requires --fetch-start and --fetch-end")
    return args


def get_stages(
    with_reports: bool,
    fetch_start: str | None = None,
    fetch_end: str | None = None,
    force_fetch: bool = False,
) -> list[tuple[str, list[str]]]:
    stages = [(description, command.copy()) for description, command in CORE_STAGES]
    if with_reports:
        stages.insert(1, REPORT_STAGE)
    if fetch_start and fetch_end:
        extract_command = [
            "extract_crmls.py",
            "--start-month",
            fetch_start,
            "--end-month",
            fetch_end,
        ]
        if force_fetch:
            extract_command.append("--force")
        stages.insert(0, ("Extract monthly CRMLS data", extract_command))
    return stages


def run_pipeline(stages: list[tuple[str, list[str]]]) -> int:
    pipeline_started = time.perf_counter()

    for position, (description, command) in enumerate(stages, start=1):
        script_name = command[0]
        print(
            f"\n[{position}/{len(stages)}] {description} ({script_name})",
            flush=True,
        )
        stage_started = time.perf_counter()

        subprocess.run(
            [sys.executable, str(PROJECT_DIR / script_name), *command[1:]],
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
    return run_pipeline(
        get_stages(
            args.with_reports,
            args.fetch_start,
            args.fetch_end,
            args.force_fetch,
        )
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nPipeline cancelled.", file=sys.stderr)
        raise SystemExit(130)
