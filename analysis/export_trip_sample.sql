-- Exports that need the trip-level sample (local only; not run by GitHub Actions).
-- Run from the project root:  python src/export.py analysis/export_trip_sample.sql

-- Tipping by hour (clean rows only)
COPY (
    SELECT trip_hour,
           AVG(CASE WHEN tip > 0 THEN 1 ELSE 0 END)        AS share_trips_tipped,
           AVG(tip)                                        AS avg_tip
    FROM main.fct_trips
    WHERE is_clean
    GROUP BY 1 ORDER BY 1
) TO 'dashboard/tipping_by_hour.csv' (HEADER);

-- Trip length distribution in 1-mile buckets (clean rows only, capped at 30+)
COPY (
    SELECT LEAST(FLOOR(trip_miles), 30)                    AS miles_bucket,
           COUNT(*)                                        AS trips
    FROM main.fct_trips
    WHERE is_clean
    GROUP BY 1 ORDER BY 1
) TO 'dashboard/trip_length_distribution.csv' (HEADER);
