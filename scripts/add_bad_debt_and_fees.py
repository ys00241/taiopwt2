#!/usr/bin/env python3
"""
One-shot migration script: add bad_debt column and create membership_fees table.

Creates:
  - bad_debt column on members table (via raw SQL for SQLite)
  - membership_fees table (via SQLAlchemy create_all)

Usage:
    source .venv/bin/activate
    python scripts/add_bad_debt_and_fees.py
"""

import os
import sys

# ── Flask app bootstrap ──────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
os.environ.setdefault("FLASK_ENV", "development")

from app import create_app
from app.extensions import db
from sqlalchemy import text


def main():
    app = create_app("development")
    with app.app_context():
        print(f"Database: {app.config.get('SQLALCHEMY_DATABASE_URI')}")

        # 1. Create all tables (new membership_fees table, etc.)
        db.create_all()
        print("✓ Tables created / verified.")

        # 2. Add bad_debt column to members table if not exists (SQLite syntax)
        try:
            db.session.execute(text("ALTER TABLE members ADD COLUMN bad_debt INTEGER DEFAULT 0"))
            db.session.commit()
            print("✓ Added bad_debt column to members table.")
        except Exception as e:
            # Column may already exist — that's fine
            db.session.rollback()
            print(f"ℹ bad_debt column may already exist: {e}")

        print("Migration complete.")


if __name__ == "__main__":
    main()
