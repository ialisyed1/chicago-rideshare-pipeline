-- One row per trip (trip-level sample), with area keys and the cleanliness flag
-- used to exclude suspicious rows from fare and duration KPIs.
select
    t.*,
    coalesce(t.pickup_area_id, 0)  as pickup_area_key,
    coalesce(t.dropoff_area_id, 0) as dropoff_area_key,
    coalesce(
        t.trip_seconds between 1 and 21600
        and t.trip_miles > 0 and t.trip_miles <= 150
        and t.fare between 0 and 500
        and abs(t.trip_total - (t.fare + t.tip + t.fees)) <= 3,
        false
    ) as is_clean
from {{ ref('stg_trips') }} t
