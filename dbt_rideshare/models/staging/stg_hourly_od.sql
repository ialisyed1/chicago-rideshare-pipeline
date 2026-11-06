-- One row per date, hour, pickup area, dropoff area and shared flag, with typed measures.
select
    cast(trip_date as date)                               as trip_date,
    try_cast(trip_hour as integer)                        as trip_hour,
    try_cast(pickup_community_area as integer)            as pickup_area_id,
    try_cast(dropoff_community_area as integer)           as dropoff_area_id,
    coalesce(try_cast(shared_trip_authorized as boolean), false) as is_shared_requested,
    try_cast(trips as bigint)                             as trips,
    try_cast(miles as double)                             as miles,
    try_cast(seconds as double)                           as seconds,
    try_cast(fare as double)                              as fare,
    try_cast(tip as double)                               as tip,
    try_cast(fees as double)                              as fees,
    try_cast(total as double)                             as trip_total
from {{ source('raw', 'hourly_od') }}
