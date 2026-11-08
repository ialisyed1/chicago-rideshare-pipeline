"""Data-quality checks on the raw trip-level Parquet files.

Usage (from the project root):  python src/quality_checks.py
Writes: docs/dq_report.md and data/quarantine/failed_rows.parquet
Exits non-zero if a BLOCKING check fails, so the pipeline stops.
"""
import glob
import os
import sys
from datetime import datetime

import duckdb

RAW = "data/raw/trips/*/*.parquet"

if not glob.glob(RAW):
    print("No trip-level files found in data/raw/trips. Run: python src/extract.py raw --start ... --end ...")
    sys.exit(1)

os.makedirs("data/quarantine", exist_ok=True)
os.makedirs("docs", exist_ok=True)
con = duckdb.connect()

# Typed view over the raw strings. TRY_CAST turns bad values into NULL instead of crashing.
con.execute(f"""
    CREATE OR REPLACE VIEW trips AS
    SELECT
        trip_id,
        CAST(trip_date AS DATE)                          AS partition_date,
        TRY_CAST(trip_start_timestamp AS TIMESTAMP)      AS start_ts,
        TRY_CAST(trip_end_timestamp   AS TIMESTAMP)      AS end_ts,
        TRY_CAST(trip_seconds AS DOUBLE)                 AS trip_seconds,
        TRY_CAST(trip_miles   AS DOUBLE)                 AS trip_miles,
        TRY_CAST(pickup_community_area  AS INTEGER)      AS pickup_area,
        TRY_CAST(dropoff_community_area AS INTEGER)      AS dropoff_area,
        TRY_CAST(fare AS DOUBLE)                         AS fare,
        TRY_CAST(tip  AS DOUBLE)                         AS tip,
        TRY_CAST(additional_charges AS DOUBLE)           AS fees,
        TRY_CAST(trip_total AS DOUBLE)                   AS trip_total
    FROM read_parquet('{RAW}', hive_partitioning = true, union_by_name = true)
""")

# Each check: (name, severity, SQL condition that marks a row as FAILING).
# Tune thresholds after inspecting the quarantine file, and record why in the report.
ROW_CHECKS = [
    ("trip_id is null",                 "blocking", "trip_id IS NULL"),
    ("start timestamp unparseable",     "blocking", "start_ts IS NULL"),
    ("start outside partition date",    "blocking", "CAST(start_ts AS DATE) <> partition_date"),
    ("end before start",                "warning",  "end_ts < start_ts"),
    ("duration <= 0 or > 6 hours",      "warning",  "trip_seconds <= 0 OR trip_seconds > 21600"),
    ("miles <= 0 or > 150",             "warning",  "trip_miles <= 0 OR trip_miles > 150"),
    ("negative money value",            "warning",  "fare < 0 OR tip < 0 OR fees < 0"),
    ("fare > $500",                     "warning",  "fare > 500"),
    ("total != fare+tip+fees (+/- $3)", "warning",  "ABS(trip_total - (fare + tip + fees)) > 3"),
    ("pickup area not in 1-77",         "warning",  "pickup_area NOT BETWEEN 1 AND 77"),
]

total = con.execute("SELECT COUNT(*) FROM trips").fetchone()[0]
dupes = con.execute(
    "SELECT COUNT(*) - COUNT(DISTINCT trip_id) FROM trips WHERE trip_id IS NOT NULL"
).fetchone()[0]

results = []
for name, severity, cond in ROW_CHECKS:
    n = con.execute(f"SELECT COUNT(*) FROM trips WHERE {cond}").fetchone()[0]
    results.append((name, severity, n))
results.append(("duplicate trip_id", "blocking", dupes))

# Null rates are informative (privacy suppression is expected), not failures.
null_rates = con.execute("""
    SELECT
        AVG(CASE WHEN pickup_area  IS NULL THEN 1 ELSE 0 END),
        AVG(CASE WHEN dropoff_area IS NULL THEN 1 ELSE 0 END),
        AVG(CASE WHEN fare         IS NULL THEN 1 ELSE 0 END)
    FROM trips
""").fetchone()

# Quarantine every row that fails any check, so analysts can inspect it.
any_fail = " OR ".join(f"({c})" for _, _, c in ROW_CHECKS)
con.execute(f"""
    COPY (SELECT * FROM trips WHERE {any_fail})
    TO 'data/quarantine/failed_rows.parquet' (FORMAT PARQUET)
""")
failed_rows = con.execute(f"SELECT COUNT(*) FROM trips WHERE {any_fail}").fetchone()[0]
pass_rate = 1 - failed_rows / total if total else 0

lines = [
    "# Data quality report",
    "",
    f"Run at {datetime.now():%Y-%m-%d %H:%M}. Rows checked: {total:,}. "
    f"Rows passing every check: {pass_rate:.2%}.",
    "",
    "| Check | Severity | Failing rows | % of rows |",
    "| --- | --- | ---: | ---: |",
]
for name, severity, n in results:
    pct = n / total if total else 0
    lines.append(f"| {name} | {severity} | {n:,} | {pct:.3%} |")
lines += [
    "",
    "Null rates (expected, from privacy suppression or trips outside Chicago): "
    f"pickup area {null_rates[0]:.2%}, dropoff area {null_rates[1]:.2%}, fare {null_rates[2]:.2%}.",
    "",
    "## Decisions",
    "",
]
# Keep any hand-written decisions from the previous report, so re-runs
# (including the weekly CI job) don't wipe them out.
REPORT = "docs/dq_report.md"
previous = open(REPORT).read() if os.path.exists(REPORT) else ""
kept = previous.split("## Decisions", 1)[1].strip() if "## Decisions" in previous else ""
lines += kept.splitlines() if kept else [
    "<!-- One sentence per threshold you tuned and why. Example: Trips over 6 hours are kept but flagged; -->",
    "<!-- most are likely drivers forgetting to end the trip. -->",
]
with open(REPORT, "w") as f:
    f.write("\n".join(lines) + "\n")

print("\n".join(lines[:len(results) + 6]))
blocking = [r for r in results if r[1] == "blocking" and r[2] > 0]
if total == 0 or blocking:
    print("BLOCKING checks failed; stopping the pipeline.")
    sys.exit(1)
print("All blocking checks passed.")
