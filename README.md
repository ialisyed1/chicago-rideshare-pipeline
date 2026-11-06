# Chicago Rideshare Demand Pipeline & KPI Dashboard

**Live dashboard:** <Tableau Public link>  ·  **Data refreshed weekly** via GitHub Actions

<!-- ![Dashboard screenshot](dashboard/screenshot.png) -->

## The question
Where and when is rideshare demand in Chicago concentrated, how is it priced, and how is it
changing? Framed for a city policy team deciding where to focus curb-management efforts.
See [docs/kpi_brief.md](docs/kpi_brief.md).

## Key findings
- <finding + number + so-what>
- <finding + number + so-what>
- <finding + number + so-what>

Full write-up: [docs/insights_memo.md](docs/insights_memo.md)

## Architecture

```text
Chicago Data Portal API (dataset 6dvr-xwnh)
        │  src/extract.py  (paging, retries, idempotent daily partitions)
        ▼
data/raw/*.parquet  (raw text, partitioned by trip_date)
        │  src/quality_checks.py  (blocking vs warning checks, quarantine)
        ▼
DuckDB + dbt  (staging → star schema → KPI mart, with tests)
        │  src/export.py + analysis/*.sql
        ▼
dashboard/*.csv  ──►  Tableau Public
GitHub Actions runs extract → dbt build → export every Monday.
```

<!-- Replace with a screenshot of the dbt lineage graph (dbt docs serve). -->

## Data quality
<N> checks; <Y>% of rows pass every check. Full report: [docs/dq_report.md](docs/dq_report.md)

## Design decisions
- **Two-tier data:** one month of trip-level data for quality checks and trip-level metrics,
  plus server-side hourly aggregates for all history. Pulling every raw trip would be tens of
  millions of rows a year, too much for a laptop and a free scheduler.
- **ELT:** raw data stays as text; all typing happens in dbt staging models.
- **Idempotent loads:** each day is its own file, overwritten on re-run. The weekly job
  re-pulls the last 45 days to catch late or corrected records.
- **Reconciliation:** `src/reconcile.py` checks that aggregated daily counts match trip-level counts.

## Project structure

```text
src/
  extract.py          API → Parquet (raw or aggregated)
  quality_checks.py   DQ checks → docs/dq_report.md + quarantine file
  reconcile.py        trip-level vs aggregated count check
  export.py           runs analysis/*.sql → dashboard/*.csv
  run_pipeline.py     runs every step in order
analysis/             export SQL for the dashboard
dbt_rideshare/        dbt project (sources, staging, marts, tests, seed)
docs/                 KPI brief, data dictionary, DQ report, insights memo
dashboard/            exported CSVs + screenshots
.github/workflows/    weekly GitHub Actions job
.vscode/              tasks, debug configs, recommended extensions
```

## How to run it

1. Clone the repo and create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate          # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` to `.env` and add your free Chicago Data Portal app token.
3. Test one day, then pull data:
   ```bash
   python src/extract.py raw --start 2025-09-02 --end 2025-09-02
   python src/extract.py raw --start 2025-09-01 --end 2025-09-30
   python src/extract.py agg --start 2025-01-01
   ```
4. Check, model and export:
   ```bash
   python src/quality_checks.py
   cd dbt_rideshare && dbt seed --profiles-dir . && dbt build --profiles-dir . && cd ..
   python src/reconcile.py
   python src/export.py analysis/export.sql
   python src/export.py analysis/export_trip_sample.sql
   ```
   Or run everything at once: `python src/run_pipeline.py --start 2025-01-01 --sample-month 2025-09`

In VS Code, every step is also available under **Terminal > Run Task**.

## Limitations and next steps
- Fares rounded to $2.50 and times to 15 minutes by the City for privacy.
- No company-level breakdown (not in the data).
- Next: weather join, weekly demand forecast, Great Expectations, Google Sheets auto-refresh for Tableau.
# chicago-rideshare-pipeline
