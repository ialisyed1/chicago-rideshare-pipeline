# Data dictionary

Source: City of Chicago, [Transportation Network Providers - Trips (2025-)](https://data.cityofchicago.org/d/6dvr-xwnh), dataset `6dvr-xwnh`.
The interactive version (with lineage) is `dbt docs serve` in `dbt_rideshare/`.

## fct_trips (one row per trip, trip-level sample)

| Column | Type | Description |
| --- | --- | --- |
| trip_id | varchar | Unique trip identifier from the City |
| start_ts / end_ts | timestamp | Trip start and end, Chicago local time, rounded to 15 minutes |
| trip_date | date | Date the trip started |
| trip_hour | integer | Hour the trip started (0-23) |
| trip_seconds | double | Trip duration in seconds |
| trip_miles | double | Trip distance in miles |
| pickup_area_key / dropoff_area_key | integer | Community area 1-77; 0 = outside Chicago or suppressed |
| fare | double | Fare, rounded to the nearest $2.50 |
| tip | double | Tip, rounded to the nearest $1.00; cash tips not recorded |
| fees | double | Taxes, fees and other charges |
| trip_total | double | Total charged for the trip |
| is_shared_requested | boolean | Rider agreed to a shared trip (whether or not it was shared) |
| trips_pooled | integer | Number of trips pooled together |
| is_clean | boolean | False if the trip fails any warning-level DQ rule |

## fct_hourly_demand (one row per date, hour, origin, destination, shared flag)

| Column | Type | Description |
| --- | --- | --- |
| trip_date | date | Date |
| trip_hour | integer | Hour of day (0-23) |
| pickup_area_key / dropoff_area_key | integer | Community area 1-77; 0 = outside Chicago or suppressed |
| is_shared_requested | boolean | Shared ride requested |
| trips | bigint | Number of trips |
| miles, seconds, fare, tip, fees, trip_total | double | Sums for the group |

## mart_daily_kpis (one row per day)

| Column | Type | Description |
| --- | --- | --- |
| trip_date | date | Date |
| day_name / is_weekend | varchar / boolean | From dim_date |
| trips | bigint | Total trips |
| gross_bookings | double | Sum of trip_total |
| avg_fare | double | Total fare / trips |
| fare_per_mile | double | Total fare / total miles |
| fee_share | double | Fees / trip_total |
| avg_trip_minutes | double | Total seconds / trips / 60 |
| shared_request_share | double | Share of trips with a shared ride requested |

## Dimensions
- **dim_date:** one row per day from 2025-01-01 to today (year, month, day name, weekend flag).
- **dim_community_area:** the 77 community areas (from `seeds/community_areas.csv`) plus key 0.
