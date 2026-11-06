-- One row per trip: types cast, columns renamed, duplicates removed.
with src as (
    select * from {{ source('raw', 'trips') }}
)

select
    trip_id,
    cast(trip_start_timestamp as timestamp)               as start_ts,
    cast(trip_end_timestamp as timestamp)                 as end_ts,
    cast(cast(trip_start_timestamp as timestamp) as date) as trip_date,
    hour(cast(trip_start_timestamp as timestamp))         as trip_hour,
    try_cast(trip_seconds as double)                      as trip_seconds,
    try_cast(trip_miles as double)                        as trip_miles,
    try_cast(pickup_community_area as integer)            as pickup_area_id,
    try_cast(dropoff_community_area as integer)           as dropoff_area_id,
    try_cast(fare as double)                              as fare,
    try_cast(tip as double)                               as tip,
    try_cast(additional_charges as double)                as fees,
    try_cast(trip_total as double)                        as trip_total,
    coalesce(try_cast(shared_trip_authorized as boolean), false) as is_shared_requested,
    try_cast(trips_pooled as integer)                     as trips_pooled
from src
where trip_id is not null
qualify row_number() over (partition by trip_id order by trip_end_timestamp desc) = 1
