"""Run a SQL file of COPY statements against the warehouse to export dashboard CSVs.

Usage (from the project root):
    python src/export.py                               # analysis/export.sql
    python src/export.py analysis/export_trip_sample.sql
"""
import os
import sys

import duckdb

sql_file = sys.argv[1] if len(sys.argv) > 1 else "analysis/export.sql"
os.makedirs("dashboard", exist_ok=True)

con = duckdb.connect("warehouse/rideshare.duckdb")
count = 0
# Drop comment lines *before* splitting on ";" so a semicolon inside a comment
# doesn't produce a broken statement.
sql = "\n".join(line for line in open(sql_file).read().splitlines()
                if not line.strip().startswith("--"))
for body in sql.split(";"):
    if body.strip():
        con.execute(body)
        count += 1
print(f"Export complete: ran {count} statements from {sql_file}")
