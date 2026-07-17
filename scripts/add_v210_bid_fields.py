#!/usr/bin/env python3
"""
One-shot migration script: add referrer_id and operator columns to bids table.

Creates:
  - referrer_id column on bids table (FK to members.member_id, nullable)
  - operator column on bids table (VARCHAR(100), default '')

Usage:
    source .venv/bin/activate
    python scripts/add_v210_bid_fields.py
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

        # 1. Ensure any new models/tables are created
        db.create_all()
        print("✓ Tables created / verified.")

        # 2. Add referrer_id column to bids table (nullable FK)
        try:
            db.session.execute(text(
                "ALTER TABLE bids ADD COLUMN referrer_id INTEGER REFERENCES members(member_id)"
            ))
            db.session.commit()
            print("✓ Added referrer_id column to bids table.")
        except Exception as e:
            db.session.rollback()
            print(f"ℹ referrer_id column may already exist: {e}")

        # 3. Add operator column to bids table
        try:
            db.session.execute(text(
                "ALTER TABLE bids ADD COLUMN operator VARCHAR(100) DEFAULT ''"
            ))
            db.session.commit()
            print("✓ Added operator column to bids table.")
        except Exception as e:
            db.session.rollback()
            print(f"ℹ operator column may already exist: {e}")

        print("Migration complete.")


if __name__ == "__main__":
    main()
