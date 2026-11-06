-- One row per calendar day from the start of the dataset to today.
select
    cast(d as date)         as date_day,
    year(d)                 as year,
    month(d)                as month,
    monthname(d)            as month_name,
    dayofweek(d)            as day_of_week,   -- 0 = Sunday
    dayname(d)              as day_name,
    dayofweek(d) in (0, 6)  as is_weekend
from generate_series(date '2025-01-01', current_date, interval 1 day) as t(d)
