"""Reconciliation check: do the server-side hourly aggregates agree with the trip-level sample?

For every date present in both, compares trip counts from fct_trips (trip level)
with fct_hourly_demand (aggregated by the API). They should match closely; a large
gap means a paging bug, a partial download, or data that changed between pulls.

Usage (from the project root, after dbt build):  python src/reconcile.py
"""
import sys

import duckdb

TOLERANCE = 0.005  # 0.5% difference allowed

con = duckdb.connect("warehouse/rideshare.duckdb", read_only=True)
rows = con.execute("""
    WITH trip_level AS (
        SELECT trip_date, COUNT(*) AS trips FROM main.fct_trips GROUP BY 1
    ),
    aggregated AS (
        SELECT trip_date, SUM(trips) AS trips FROM main.fct_hourly_demand GROUP BY 1
    )
    SELECT t.trip_date, t.trips AS trip_level, a.trips AS aggregated,
           ABS(t.trips - a.trips) / NULLIF(a.trips, 0) AS pct_diff
    FROM trip_level t
    JOIN aggregated a USING (trip_date)
    ORDER BY t.trip_date
""").fetchall()

if not rows:
    print("No overlapping dates. Extract a trip-level month that is also covered by the aggregates.")
    sys.exit(1)

bad = [r for r in rows if r[3] is None or r[3] > TOLERANCE]
print(f"Compared {len(rows)} days. Days outside {TOLERANCE:.1%} tolerance: {len(bad)}")
for d, t, a, p in bad[:20]:
    print(f"  {d}: trip-level {t:,} vs aggregated {a:,} ({p:.2%})")
sys.exit(1 if bad else 0)
