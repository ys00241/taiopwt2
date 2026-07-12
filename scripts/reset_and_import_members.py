#!/usr/bin/env python3
"""
寶榮堂花炮會 — 重置 DB + Import 新 Members CSV.

動作:
1. 清空所有 data table（members, bids, this_year_items, PL, daily_entries, live_income, expenses, sponsors, live_expenses, membership_fees）
2. 保留 Item master + User + Photo/PhotoLink
3. 加新 columns（end_year, name_alais, group_name, referrer）via migration
4. Import members CSV（54 個新 member records）
5. Seed Edition table（2020-2026）
"""

import csv
import uuid
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask
from app.extensions import db
from app.models.member import Member
from app.models.item import Item
from app.models.edition import Edition
from app.models.bid import Bid
from app.models.this_year_item import ThisYearItem
from app.models.pl import PL
from app.models.daily_entry import DailyEntry
from app.models.live_income import LiveIncome
from app.models.expense import Expense
from app.models.sponsor import Sponsor
from app.models.live_expense import LiveExpense
from app.models.membership_fee import MembershipFee
from app.models.user import User
from app.models.photo import Photo
from app.models.photo_link import PhotoLink


def create_app():
    from config import Config
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app


def main():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("寶榮堂花炮會 — Database Reset & Member Import")
        print("=" * 60)

        # ── Step 1: Migration — add new columns ──
        print("\n📦 Step 1: Running migration (add new columns)...")
        try:
            db.session.execute("ALTER TABLE members ADD COLUMN end_year INTEGER")
        except Exception:
            print("  ℹ end_year column already exists")
        try:
            db.session.execute("ALTER TABLE members ADD COLUMN name_alais VARCHAR(200)")
        except Exception:
            print("  ℹ name_alais column already exists")
        try:
            db.session.execute("ALTER TABLE members ADD COLUMN group_name VARCHAR(200)")
        except Exception:
            print("  ℹ group_name column already exists")
        try:
            db.session.execute("ALTER TABLE members ADD COLUMN referrer VARCHAR(200)")
        except Exception:
            print("  ℹ referrer column already exists")
        db.session.commit()

        # ── Step 2: Delete all data tables ──
        print("\n🗑️  Step 2: Deleting all data...")
        tables_to_clear = [
            MembershipFee.__tablename__,
            LiveExpense.__tablename__,
            Sponsor.__tablename__,
            Expense.__tablename__,
            LiveIncome.__tablename__,
            DailyEntry.__tablename__,
            PL.__tablename__,
            ThisYearItem.__tablename__,
            Bid.__tablename__,
            PhotoLink.__tablename__,
            Member.__tablename__,
        ]
        for table in tables_to_clear:
            db.session.execute(f"DELETE FROM {table}")
            print(f"  ✅ Cleared: {table}")
        db.session.commit()

        # ── Step 3: Import members from CSV ──
        csv_path = os.environ.get("MEMBER_CSV", "")
        if not csv_path:
            csv_path = str(PROJECT_ROOT / "csv_exports" / "members-mode.csv")

        print(f"\n📥 Step 3: Importing members from {csv_path}")
        if not os.path.exists(csv_path):
            print(f"  ❌ CSV not found: {csv_path}")
            print("  💡 Set MEMBER_CSV env var or place csv at csv_exports/members-mode.csv")
            sys.exit(1)

        member_id_seq = 100
        imported = 0
        skipped = 0

        with open(csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = (row.get("name") or "").strip()
                if not name:
                    skipped += 1
                    continue

                # Referrer field (CSV has header typo 'refererr')
                referrer = (row.get("refererr") or row.get("referrer") or "").strip()

                # Group field
                group_name = (row.get("Group") or row.get("group") or "").strip()

                # Bad debt
                bad_debt_val = (row.get("bad_debt") or "").strip()
                bad_debt = bad_debt_val == "1" or bad_debt_val.lower() == "true"

                # Status
                status = (row.get("status") or "active").strip()

                # Member type
                member_type = (row.get("member_type") or "member").strip()

                # End year
                end_year_str = (row.get("end_year") or "").strip()
                end_year = int(end_year_str) if end_year_str else None

                # First year
                first_year_str = (row.get("first_year") or "").strip()
                first_year = int(first_year_str) if first_year_str else None

                # Name alais
                name_alais = (row.get("name_alais") or "").strip()

                # Phone
                phone = (row.get("phone") or "").strip() or None
                phone_2 = (row.get("phone_2") or "").strip() or None
                home_address = (row.get("home_address") or "").strip() or None

                member = Member(
                    id=str(uuid.uuid4()),
                    member_id=member_id_seq,
                    name=name,
                    name_alais=name_alais or None,
                    group_name=group_name or None,
                    referrer=referrer or None,
                    phone=phone,
                    phone_2=phone_2,
                    home_address=home_address,
                    first_year=first_year,
                    end_year=end_year,
                    member_type=member_type,
                    status=status,
                    bad_debt=bad_debt,
                )
                db.session.add(member)
                member_id_seq += 1
                imported += 1

        db.session.commit()
        print(f"  ✅ Imported: {imported} members (skipped {skipped} empty rows)")

        # ── Step 4: Seed Editions ──
        print("\n📅 Step 4: Seeding Editions (2020-2026)...")
        for y in range(2020, 2027):
            existing = Edition.query.filter_by(year=y).first()
            if not existing:
                edition = Edition(year=y, name=f"{y}年度", status="active")
                db.session.add(edition)
        db.session.commit()
        print("  ✅ Editions seeded")

        # ── Step 5: Summary ──
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        print(f"  Members:       {Member.query.count()}")
        print(f"  Items (kept):  {Item.query.count()}")
        print(f"  Editions:      {Edition.query.count()}")
        print(f"  Bids:          {Bid.query.count()}")
        print(f"  ThisYearItems: {ThisYearItem.query.count()}")
        print(f"\n✅ Done! Members are ready for 2025/26 data entry.")
        print("=" * 60)


if __name__ == "__main__":
    main()
