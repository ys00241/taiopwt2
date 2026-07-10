#!/usr/bin/env python3
"""
寶榮堂花炮會 — Database Initialization Script.

Creates all tables (via SQLAlchemy) and loads CSV exports into the database.
Run from the project root::

    cd /opt/data/taiopwt2
    python init_db.py                   # fresh database
    python init_db.py --year 2026       # override default year
    python init_db.py --import-only     # only import CSV, skip DDL

CSV files are expected in ``csv_exports/``.
"""

import argparse
import csv
import uuid
import sys
from pathlib import Path

# Ensure the project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask
from config import Config
from app.extensions import db
from app.models import *  # noqa: F401, F403 — register all models


def create_tables(app: Flask) -> None:
    """Create all tables defined by the SQLAlchemy models."""
    with app.app_context():
        db.create_all()
        print("  ✓ All tables created / verified.")


def load_csv(app: Flask, table_name: str, csv_path: Path,
             fill_columns: dict[str, object] | None = None) -> None:
    """Load rows from *csv_path* into *table_name*.

    Parameters
    ----------
    fill_columns:
        Column → value pairs to auto-fill when the column is missing
        from the CSV header.  The value can be:
        - A literal (str, int, float) — used as-is for every row.
        - ``"__uuid__"`` — generate a UUID4 string per row.
        - ``"__seq__"`` — generate sequential 1-based integers per row.
    """
    if not csv_path.exists():
        print(f"  - SKIP {csv_path.name}: file not found")
        return
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    if not rows:
        print(f"  - SKIP {csv_path.name}: empty")
        return

    # Determine final column list and build value generators
    csv_columns = list(rows[0].keys())
    fill = dict(fill_columns or {})
    extra_columns = [c for c in fill if c not in csv_columns]
    all_columns = csv_columns + extra_columns

    # Build per-column value extractors
    seq_counters: dict[str, list[int]] = {}

    def col_value(row: dict, col: str):
        if col in csv_columns:
            return row.get(col)
        # Auto-fill
        spec = fill[col]
        if spec == "__uuid__":
            return str(uuid.uuid4())
        elif spec == "__seq__":
            counter = seq_counters.setdefault(col, [0])
            counter[0] += 1
            return counter[0]
        else:
            return spec

    placeholders = ",".join(["?" for _ in all_columns])
    col_names = ",".join(all_columns)

    with app.app_context():
        conn = db.engine.raw_connection()
        cursor = conn.cursor()

        # Skip if table already has data
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        if cursor.fetchone()[0]:
            print(f"  - SKIP {csv_path.name}: {table_name} already has data")
            conn.close()
            return

        for row_idx, row in enumerate(rows, start=2):
            values = [col_value(row, c) for c in all_columns]
            try:
                cursor.execute(
                    f"INSERT INTO {table_name} ({col_names}) VALUES ({placeholders})",
                    values,
                )
            except Exception as e:
                print(f"  - ERROR row {row_idx} in {csv_path.name}: {e}")
                print(f"    cols: {all_columns}")
                print(f"    vals: {values}")
                conn.rollback()
                conn.close()
                return

        conn.commit()
        conn.close()
    print(f"  ✓ {csv_path.name:30s} -> {table_name}  ({len(rows)} rows)")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Initialize the 寶榮堂花炮會 database from CSV exports."
    )
    parser.add_argument(
        "--import-only",
        action="store_true",
        help="Skip table creation; only import CSV data.",
    )
    parser.add_argument(
        "--year",
        type=int,
        default=2026,
        help="Target year for workflow tables that lack a year column (default: 2026).",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("寶榮堂花炮會 — Database Initialization")
    print("=" * 60)

    # --- Build a minimal Flask app ---
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)

    # --- Create tables ---
    if not args.import_only:
        print("\nCreating tables...")
        create_tables(app)

    # --- Load CSV data ---
    csv_dir = PROJECT_ROOT / "csv_exports"
    print(f"\nLoading CSV data from: {csv_dir}")
    print("-" * 60)

    # Core data tables (from original CSV exports)
    # fill_columns specifies which missing columns to auto-generate
    core_table_map = [
        ("members", "members.csv",
         {"id": "__uuid__", "member_id": "__seq__"}),
        ("editions", "editions.csv",
         {"id": "__uuid__"}),
        ("items", "items.csv",
         {"id": "__uuid__"}),
        ("item_years", "item_years.csv", None),
        ("bids", "bids.csv",
         {"id": "__uuid__", "record_id": "__seq__"}),
        ("pl", "pl.csv",
         {"id": "__uuid__", "record_id": "__seq__"}),
    ]

    for table_name, csv_file, fill in core_table_map:
        load_csv(app, table_name, csv_dir / csv_file, fill_columns=fill)

    # Workflow tables — these often lack a ``year`` column
    workflow_table_map = [
        ("this_year_items", "this_year_items.csv",
         {"year": args.year}),
        ("sponsors", "sponsors.csv",
         {"year": args.year}),
        ("expenses", "pre_expenses.csv",
         {"year": args.year}),
        ("daily_entries", "daily_entries.csv",
         {"year": args.year}),
    ]

    for table_name, csv_file, fill in workflow_table_map:
        load_csv(app, table_name, csv_dir / csv_file, fill_columns=fill)

    # --- Verify ---
    print(f"\nVerification:")
    with app.app_context():
        all_tables = [
            "members", "editions", "items", "item_years", "bids", "pl",
            "this_year_items", "expenses", "sponsors",
            "live_income", "live_expenses",
            "daily_entries", "photos", "photo_links",
        ]
        conn = db.engine.raw_connection()
        cursor = conn.cursor()
        for table in all_tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {table}: {count} rows")
            except Exception:
                print(f"  {table}: (not created)")
        conn.close()

    db_path = Config.SQLALCHEMY_DATABASE_URI.replace("sqlite:///", "")
    print(f"\nDatabase: {db_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
