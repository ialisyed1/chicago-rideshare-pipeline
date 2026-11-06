# Reference data

- The 77 community area names live in `dbt_rideshare/seeds/community_areas.csv` (loaded by `dbt seed`).
  Spot-check them against the City's "Boundaries - Community Areas" dataset on data.cityofchicago.org.
- For the Tableau map, download that same dataset as GeoJSON and save it here as
  `community_areas.geojson`. Join it to `dashboard/pickup_areas.csv` on the area number.
