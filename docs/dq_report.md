# Data quality report

Run at 2026-11-07 18:02. Rows checked: 7,496,069. Rows passing every check: 99.99%.

| Check | Severity | Failing rows | % of rows |
| --- | --- | ---: | ---: |
| trip_id is null | blocking | 0 | 0.000% |
| start timestamp unparseable | blocking | 0 | 0.000% |
| start outside partition date | blocking | 0 | 0.000% |
| end before start | warning | 0 | 0.000% |
| duration <= 0 or > 6 hours | warning | 40 | 0.001% |
| miles <= 0 or > 150 | warning | 633 | 0.008% |
| negative money value | warning | 0 | 0.000% |
| fare > $500 | warning | 12 | 0.000% |
| total != fare+tip+fees (+/- $3) | warning | 0 | 0.000% |
| pickup area not in 1-77 | warning | 0 | 0.000% |
| duplicate trip_id | blocking | 0 | 0.000% |

Null rates (expected, from privacy suppression or trips outside Chicago): pickup area 9.94%, dropoff area 10.43%, fare 0.33%.

## Decisions

- **No blocking failures:** all 7,496,069 September trips have a trip ID and a parseable start time, fall on their partition date, and are unique, so nothing is dropped.
- **Duration <= 0 (27 rows):** every one is exactly 0 seconds with a median fare of $0 despite a median 3.4 miles, so these look like cancelled or mis-recorded trips; they are kept but flagged (is_clean = false), which excludes them from the trip-level dashboard metrics while the aggregate trip counts still include them.
- **Duration > 6 hours (13 rows):** median 19.8 miles and $140, far too short for 6-15 hours of driving, so these are most likely drivers forgetting to end the trip; kept but flagged, and the 6-hour threshold stays.
- **Miles <= 0 (176 rows):** median 4 minutes and a $7.50 fare (the minimum), with 57% starting and ending in the same community area, so these are real very short or cancelled-with-fee trips; kept but flagged because they would distort fare per mile.
- **Miles > 150 (457 rows):** median 3 hours and $220 fare, which is consistent with genuine long-distance trips out of the city (for example to Milwaukee or Indiana), so these are real trips; kept but flagged so they don't skew average trip length.
- **Fare > $500 (12 rows):** all 100-409 miles and 2-6 hours long at $1.50-$10.40 per mile, so they are real long trips rather than data-entry errors; kept but flagged.
- **Missing pickup/dropoff area (~10%):** expected from the City's privacy suppression and trips outside Chicago; these trips are grouped as area 0 rather than removed.
- **Missing fare (0.33%, 24,769 trips):** kept in trip counts, but dbt marks them is_clean = false because fare, fee and tip metrics can't be computed for them. In total fct_trips has 25,322 unclean trips (0.34%), almost all of them missing a fare.
