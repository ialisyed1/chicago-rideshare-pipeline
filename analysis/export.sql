-- Dashboard exports built from the aggregated history (runs locally and in GitHub Actions).
-- Run from the project root:  python src/export.py analysis/export.sql

-- 1. Monthly demand and month-over-month growth
COPY (
    SELECT
        date_trunc('month', trip_date)                     AS month,
        SUM(trips)                                         AS trips,
        SUM(trips) / LAG(SUM(trips)) OVER (ORDER BY date_trunc('month', trip_date)) - 1 AS mom_growth
    FROM main.fct_hourly_demand
    GROUP BY 1 ORDER BY 1
) TO 'dashboard/monthly_trend.csv' (HEADER);

-- 2. When: average trips per hour, by weekday (heatmap)
COPY (
    SELECT d.day_name, d.day_of_week, f.trip_hour,
           SUM(f.trips) / COUNT(DISTINCT f.trip_date)      AS avg_trips
    FROM main.fct_hourly_demand f
    JOIN main.dim_date d ON d.date_day = f.trip_date
    GROUP BY 1, 2, 3
    ORDER BY 2, 3
) TO 'dashboard/hour_weekday.csv' (HEADER);

-- 3. Where: trips and share by pickup community area (map)
COPY (
    SELECT a.area_id, a.area_name,
           SUM(f.trips)                                    AS trips,
           SUM(f.trips) / SUM(SUM(f.trips)) OVER ()        AS share_of_trips,
           SUM(f.fare) / NULLIF(SUM(f.miles), 0)           AS fare_per_mile
    FROM main.fct_hourly_demand f
    JOIN main.dim_community_area a ON a.area_id = f.pickup_area_key
    GROUP BY 1, 2 ORDER BY trips DESC
) TO 'dashboard/pickup_areas.csv' (HEADER);

-- 4. Top 25 origin-destination pairs
COPY (
    SELECT o.area_name AS origin, dst.area_name AS destination,
           SUM(f.trips) AS trips
    FROM main.fct_hourly_demand f
    JOIN main.dim_community_area o   ON o.area_id   = f.pickup_area_key
    JOIN main.dim_community_area dst ON dst.area_id = f.dropoff_area_key
    WHERE f.pickup_area_key <> 0 AND f.dropoff_area_key <> 0
    GROUP BY 1, 2 ORDER BY trips DESC LIMIT 25
) TO 'dashboard/top_od_pairs.csv' (HEADER);

-- 5. Price: fare per mile by hour of day (a proxy for surge pricing)
COPY (
    SELECT trip_hour,
           SUM(fare) / NULLIF(SUM(miles), 0)               AS fare_per_mile,
           SUM(fare) / NULLIF(SUM(trips), 0)               AS avg_fare
    FROM main.fct_hourly_demand
    GROUP BY 1 ORDER BY 1
) TO 'dashboard/price_by_hour.csv' (HEADER);

-- 6. Airport share: trips starting or ending at O'Hare (community area 76) by month
COPY (
    SELECT date_trunc('month', trip_date)                  AS month,
           SUM(CASE WHEN pickup_area_key = 76 OR dropoff_area_key = 76 THEN trips ELSE 0 END)
               / SUM(trips)                                AS ohare_share
    FROM main.fct_hourly_demand
    GROUP BY 1 ORDER BY 1
) TO 'dashboard/airport_share.csv' (HEADER);

-- 7. Daily KPI table (headline numbers + trend lines)
COPY (SELECT * FROM main.mart_daily_kpis ORDER BY trip_date)
TO 'dashboard/daily_kpis.csv' (HEADER);
