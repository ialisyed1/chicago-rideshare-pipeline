-- One row per date, hour, origin, destination and shared flag, for all history.
select
    *,
    coalesce(pickup_area_id, 0)  as pickup_area_key,
    coalesce(dropoff_area_id, 0) as dropoff_area_key
from {{ ref('stg_hourly_od') }}
