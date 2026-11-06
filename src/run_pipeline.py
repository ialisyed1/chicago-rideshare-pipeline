"""Run the whole pipeline locally, step by step.

Usage (from the project root, with the virtual environment active):
    python src/run_pipeline.py                         # refresh last 45 days of aggregates
    python src/run_pipeline.py --start 2025-01-01      # full backfill of aggregates
    python src/run_pipeline.py --sample-month 2025-09  # also pull a trip-level month + DQ checks

Steps: extract -> (DQ checks) -> dbt seed/build -> (reconcile) -> export CSVs
"""
import argparse
import os
import shutil
import subprocess
import sys
from calendar import monthrange
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PY = sys.executable


def run(cmd: list[str], cwd: str = ROOT) -> None:
    print(f"\n>>> {' '.join(cmd)}  (in {os.path.relpath(cwd, ROOT) or '.'})", flush=True)
    result = subprocess.run(cmd, cwd=cwd)
    if result.returncode != 0:
        sys.exit(f"Step failed: {' '.join(cmd)}")


def dbt_cmd() -> str:
    """Find the dbt executable inside the same virtual environment as this Python."""
    bin_dir = os.path.dirname(PY)
    for name in ("dbt", "dbt.exe"):
        candidate = os.path.join(bin_dir, name)
        if os.path.exists(candidate):
            return candidate
    found = shutil.which("dbt")
    if not found:
        sys.exit("dbt not found. Run: pip install -r requirements.txt")
    return found


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=date.fromisoformat,
                        default=date.today() - timedelta(days=45),
                        help="Start date for aggregated extract (default: 45 days ago)")
    parser.add_argument("--sample-month", help="YYYY-MM: also extract every trip for this month")
    args = parser.parse_args()

    run([PY, "src/extract.py", "agg", "--start", str(args.start)])

    if args.sample_month:
        y, m = map(int, args.sample_month.split("-"))
        first, last = date(y, m, 1), date(y, m, monthrange(y, m)[1])
        run([PY, "src/extract.py", "raw", "--start", str(first), "--end", str(last)])

    has_trips = os.path.isdir(os.path.join(ROOT, "data", "raw", "trips"))
    if has_trips:
        run([PY, "src/quality_checks.py"])

    os.makedirs(os.path.join(ROOT, "warehouse"), exist_ok=True)
    dbt_dir = os.path.join(ROOT, "dbt_rideshare")
    dbt = dbt_cmd()
    run([dbt, "seed", "--profiles-dir", "."], cwd=dbt_dir)
    build = [dbt, "build", "--profiles-dir", "."]
    if not has_trips:
        build += ["--exclude", "stg_trips+"]
    run(build, cwd=dbt_dir)

    if has_trips:
        run([PY, "src/reconcile.py"])
        run([PY, "src/export.py", "analysis/export_trip_sample.sql"])
    run([PY, "src/export.py", "analysis/export.sql"])
    print("\nPipeline finished. Dashboard CSVs are in dashboard/.")


if __name__ == "__main__":
    main()
