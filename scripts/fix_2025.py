#!/usr/bin/env python3
"""
Fix 2025 data: create missing Edition + clear stale data, then re-import.
Run AFTER the new import_2025.py (which creates ThisYearItem + Member + Item + Bid).

Usage:
    docker cp fix_2025.py taio_pwt:/app/scripts/
    docker exec taio_pwt python scripts/fix_2025.py
    docker exec taio_pwt python scripts/import_2025.py
"""
import sys
import os
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("FLASK_ENV", "production")

from app import create_app
from app.extensions import db
from app.models.this_year_item import ThisYearItem
from app.models.bid import Bid
from app.models.edition import Edition
from app.models.member import Member
from app.models.item import Item


def main():
    app = create_app()
    with app.app_context():
        db.create_all()

        print("=" * 60)
        print("🔧 Fixing 2025 data...")
        print("=" * 60)

        # ── 1. Delete stale/partial 2025 Bid records (if any) ──
        old_bids = Bid.query.filter_by(year=2025).count()
        if old_bids:
            Bid.query.filter_by(year=2025).delete()
            print(f"  🗑️  Deleted {old_bids} stale 2025 Bid records")

        # ── 2. Create Edition 2025 if missing ──
        ed = Edition.query.filter_by(year=2025).first()
        if not ed:
            ed = Edition(
                id=str(uuid.uuid4()),
                year=2025,
                edition_no=1,
                event_date="2025-03-01",
            )
            db.session.add(ed)
            print("  ✅ Created Edition 2025")
        else:
            print("  ℹ️  Edition 2025 already exists")

        # ── 3. Verify ThisYearItem data intact ──
        tyi_count = ThisYearItem.query.filter_by(year=2025).count()
        print(f"  📦 ThisYearItems (2025): {tyi_count}")

        # ── 4. Count members/items for reference ──
        member_count = Member.query.count()
        item_count = Item.query.count()
        print(f"  👤 Members total: {member_count}")
        print(f"  📋 Items total: {item_count}")

        db.session.commit()

        print(f"\n✅ Fix complete!")
        print("   Edition 2025 created ✓")
        print("   Now run: docker exec taio_pwt python scripts/import_2025.py")
        print("   to create Bid records for 收款台")
        print("=" * 60)


if __name__ == "__main__":
    main()
