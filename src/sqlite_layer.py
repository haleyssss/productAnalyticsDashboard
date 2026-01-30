"""SQLite helpers to run SQL queries against the events data."""

from __future__ import annotations

import os
import sqlite3

import pandas as pd

DB_PATH = "data/events.sqlite"


def ensure_db(csv_path: str, db_path: str = DB_PATH) -> None:
    """Create a local SQLite db and load events if it does not exist."""
    if os.path.exists(db_path):
        csv_mtime = os.path.getmtime(csv_path)
        db_mtime = os.path.getmtime(db_path)
        if db_mtime >= csv_mtime:
            return

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    events = pd.read_csv(csv_path)
    if "event_time" in events.columns:
        events["event_time"] = pd.to_datetime(events["event_time"], errors="coerce")
        events = events.dropna(subset=["event_time"])
        events["event_time"] = events["event_time"].dt.strftime("%Y-%m-%d %H:%M:%S")

    with sqlite3.connect(db_path) as conn:
        events.to_sql("events", conn, if_exists="replace", index=False)


def run_queries(sql_path: str, db_path: str = DB_PATH) -> list[pd.DataFrame]:
    """Run each SQL statement in the file and return results as DataFrames."""
    with open(sql_path, "r", encoding="utf-8") as handle:
        sql = handle.read()

    statements = [stmt.strip() for stmt in sql.split(";") if stmt.strip()]
    results: list[pd.DataFrame] = []

    with sqlite3.connect(db_path) as conn:
        for stmt in statements:
            results.append(pd.read_sql_query(stmt, conn))

    return results
