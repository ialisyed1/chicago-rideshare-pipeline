-- One row per day with the headline KPIs the dashboard reads.
select
    f.trip_date,
    d.day_name,
    d.is_weekend,
    sum(f.trips)                                          as trips,
    sum(f.trip_total)                                     as gross_bookings,
    sum(f.fare) / nullif(sum(f.trips), 0)                 as avg_fare,
    sum(f.fare) / nullif(sum(f.miles), 0)                 as fare_per_mile,
    sum(f.fees) / nullif(sum(f.trip_total), 0)            as fee_share,
    sum(f.seconds) / nullif(sum(f.trips), 0) / 60         as avg_trip_minutes,
    sum(case when f.is_shared_requested then f.trips else 0 end)
        / nullif(sum(f.trips), 0)                         as shared_request_share
from {{ ref('fct_hourly_demand') }} f
join {{ ref('dim_date') }} d on d.date_day = f.trip_date
group by 1, 2, 3
