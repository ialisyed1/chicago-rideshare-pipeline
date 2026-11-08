"""Extract Chicago rideshare (TNP) trips from the Socrata API into Parquet.

Usage (run from the project root):
    python src/extract.py raw --start 2025-09-02 --end 2025-09-02   # test one day
    python src/extract.py raw --start 2025-09-01 --end 2025-09-30   # trip-level sample month
    python src/extract.py agg --start 2025-01-01                    # hourly aggregates, to today

Output:
    data/raw/trips/trip_date=YYYY-MM-DD/part.parquet       (raw mode)
    data/raw/hourly_od/trip_date=YYYY-MM-DD/part.parquet   (agg mode)

Re-running a day overwrites that day's file, so runs are idempotent.
"""
import argparse
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://data.cityofchicago.org/resource/6dvr-xwnh.json"
TOKEN = os.getenv("SODA_APP_TOKEN")
HEADERS = {"X-App-Token": TOKEN} if TOKEN else {}
PAGE_SIZE = 50_000
HOUR_WORKERS = 4  # parallel hourly requests per day in raw mode; keep modest to be polite to the API
DAY_WORKERS = 4   # parallel days in agg mode (each server-side group-by takes ~70s)
AGG_LIMIT = 500_000

# The API leaves out keys whose value is null, so a quiet day can be missing a
# column entirely. Re-indexing to these lists keeps every file's schema the same.
RAW_COLUMNS = [
    "trip_id", "trip_start_timestamp", "trip_end_timestamp", "trip_seconds",
    "trip_miles", "pickup_census_tract", "dropoff_census_tract",
    "pickup_community_area", "dropoff_community_area", "fare", "tip",
    "additional_charges", "trip_total", "shared_trip_authorized", "trips_pooled",
    "pickup_centroid_latitude", "pickup_centroid_longitude",
    "dropoff_centroid_latitude", "dropoff_centroid_longitude",
]
AGG_COLUMNS = [
    "trip_hour", "pickup_community_area", "dropoff_community_area",
    "shared_trip_authorized", "trips", "miles", "seconds", "fare", "tip",
    "fees", "total",
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("extract")

if not TOKEN:
    log.warning("SODA_APP_TOKEN is not set; requests will be heavily throttled. See .env.example.")


def fetch(params: dict, retries: int = 5) -> list[dict]:
    """GET one page from the API, retrying with exponential backoff."""
    for attempt in range(retries):
        try:
            resp = requests.get(BASE_URL, params=params, headers=HEADERS, timeout=180)
            if resp.status_code == 200:
                return resp.json()
            log.warning("HTTP %s: %s", resp.status_code, resp.text[:300])
        except requests.RequestException as exc:
            log.warning("Request failed: %s", exc)
        time.sleep(2 ** attempt)
    raise RuntimeError(f"Giving up after {retries} attempts: {params}")


def fetch_all(params: dict) -> pd.DataFrame:
    """Page through every result for a query using $limit / $offset."""
    rows, offset = [], 0
    while True:
        page = fetch({**params, "$limit": PAGE_SIZE, "$offset": offset})
        rows.extend(page)
        log.info("  fetched %s rows (offset %s)", len(page), offset)
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE
    return pd.DataFrame(rows)


def normalize(df: pd.DataFrame, expected: list[str]) -> pd.DataFrame:
    """Same columns in the same order every time, all stored as text (ELT: typing happens in dbt)."""
    extras = [c for c in df.columns if c not in expected]
    return df.reindex(columns=expected + extras).astype("string")


def write_partition(df: pd.DataFrame, folder: str, day: date) -> None:
    """Write one day to folder/trip_date=YYYY-MM-DD/part.parquet (overwrites)."""
    path = os.path.join(folder, f"trip_date={day}", "part.parquet")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_parquet(path, index=False)
    log.info("%s: wrote %s rows -> %s", day, len(df), path)


def day_filter(day: date) -> str:
    nxt = day + timedelta(days=1)
    return (f"trip_start_timestamp >= '{day}T00:00:00' "
            f"AND trip_start_timestamp < '{nxt}T00:00:00'")


def hour_filter(day: date, hour: int) -> str:
    start = datetime.combine(day, datetime.min.time()) + timedelta(hours=hour)
    end = start + timedelta(hours=1)
    return (f"trip_start_timestamp >= '{start:%Y-%m-%dT%H:%M:%S}' "
            f"AND trip_start_timestamp < '{end:%Y-%m-%dT%H:%M:%S}'")


def fetch_hour(day: date, hour: int) -> pd.DataFrame:
    """One hour of trips. An hour fits in one page, so no $order is needed
    (sorting this dataset server-side is extremely slow). If an hour ever fills
    a page, fall back to ordered paging so no rows are skipped or duplicated."""
    where = hour_filter(day, hour)
    page = fetch({"$where": where, "$limit": PAGE_SIZE})
    if len(page) < PAGE_SIZE:
        return pd.DataFrame(page)
    log.warning("%s hour %s filled a page; falling back to ordered paging", day, hour)
    return fetch_all({"$where": where, "$order": "trip_id"})


def extract_raw(day: date) -> None:
    """Every trip that started on `day`, fetched as 24 hourly queries in parallel."""
    with ThreadPoolExecutor(max_workers=HOUR_WORKERS) as pool:
        parts = list(pool.map(lambda h: fetch_hour(day, h), range(24)))
    df = pd.concat(parts, ignore_index=True)
    if not df.empty:
        df = df.drop_duplicates(subset="trip_id")
    if df.empty:
        log.info("%s: no rows yet, skipping", day)
        return
    write_partition(normalize(df, RAW_COLUMNS), "data/raw/trips", day)


AGG_SELECT = (
    "date_extract_hh(trip_start_timestamp) AS trip_hour, "
    "pickup_community_area, dropoff_community_area, shared_trip_authorized, "
    "count(*) AS trips, sum(trip_miles) AS miles, sum(trip_seconds) AS seconds, "
    "sum(fare) AS fare, sum(tip) AS tip, "
    "sum(additional_charges) AS fees, sum(trip_total) AS total"
)
AGG_GROUP = ("date_extract_hh(trip_start_timestamp), pickup_community_area, "
             "dropoff_community_area, shared_trip_authorized")


def extract_agg(day: date) -> None:
    """Hourly trips by origin/destination area, aggregated on the server.

    The date is not stored as a column: it comes from the folder name
    (trip_date=YYYY-MM-DD), which DuckDB reads as a column via hive partitioning.
    """
    params = {"$select": AGG_SELECT, "$where": day_filter(day), "$group": AGG_GROUP}
    # One big unsorted page (busy days have ~50k groups). Only if a day ever
    # fills it do we fall back to ordered paging, which is slower but stable.
    page = fetch({**params, "$limit": AGG_LIMIT})
    if len(page) < AGG_LIMIT:
        df = pd.DataFrame(page)
    else:
        log.warning("%s filled the agg page; falling back to ordered paging", day)
        df = fetch_all({**params, "$order": AGG_GROUP})
    if df.empty:
        log.info("%s: no rows yet, skipping", day)
        return
    write_partition(normalize(df, AGG_COLUMNS), "data/raw/hourly_od", day)


def daterange(start: date, end: date):
    d = start
    while d <= end:
        yield d
        d += timedelta(days=1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Chicago rideshare trips.")
    parser.add_argument("mode", choices=["raw", "agg"],
                        help="raw = every trip; agg = hourly origin/destination aggregates")
    parser.add_argument("--start", required=True, type=date.fromisoformat, help="YYYY-MM-DD")
    parser.add_argument("--end", type=date.fromisoformat, default=date.today(),
                        help="YYYY-MM-DD (default: today)")
    args = parser.parse_args()

    if args.end < args.start:
        parser.error("--end must be on or after --start")

    job = extract_raw if args.mode == "raw" else extract_agg
    workers = 1 if args.mode == "raw" else DAY_WORKERS  # raw already parallelizes within a day

    def run(day: date):
        try:
            job(day)
            return None
        except Exception as exc:  # keep going; report failed days at the end
            log.error("%s: FAILED: %s", day, exc)
            return day

    with ThreadPoolExecutor(max_workers=workers) as pool:
        failed = [d for d in pool.map(run, daterange(args.start, args.end)) if d]
    if failed:
        log.error("Failed days (re-run these): %s", ", ".join(map(str, failed)))
        raise SystemExit(1)
    log.info("All days succeeded.")


if __name__ == "__main__":
    main()
