# KPI brief

## Stakeholder
Chicago BACP policy team, deciding where to focus curb-management and congestion-pricing efforts.
<!-- Edit to fit the roles you're targeting: a transit agency planner, a rideshare ops lead, etc. -->

## Business questions and KPIs

| Business question | KPI | Definition |
| --- | --- | --- |
| How much demand is there, and is it growing? | Total trips; month-over-month growth | `COUNT(trips)`; `(this month / last month) - 1` |
| When is demand concentrated? | Trips by hour and weekday | Average trips per hour, by `trip_hour` and `day_of_week` |
| Where does demand start and end? | Trips by pickup area; top origin-destination pairs | Count by pickup area; count by (pickup, dropoff) |
| What does a ride cost riders? | Average fare; fare per mile | `SUM(fare) / SUM(trips)`; `SUM(fare) / SUM(miles)` |
| How much goes to fees and tips? | Fee share; tip rate | `SUM(fees) / SUM(trip_total)`; share of trips with `tip > 0` |
| Is pooling still used? | Shared-request share | Share of trips where `shared_trip_authorized = true` |
| Is the data trustworthy? | DQ pass rate | Rows passing all checks / total rows |

## Out of scope
- Company-level comparisons (Uber vs. Lyft): the City's data does not identify the company.
- Driver earnings and individual drivers.
- Trips before 2025 (separate datasets; possible extension for year-over-year).

## Known data limitations
- Trip times rounded to the nearest 15 minutes; fares to the nearest $2.50; tips to the nearest $1.00.
- Census tracts suppressed for some trips; community area blank for trips outside Chicago.
- Data is published in batches, so the most recent weeks may be incomplete.
