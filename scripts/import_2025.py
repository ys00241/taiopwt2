#!/usr/bin/env python3
"""
Import 2025 sorting data from sorting2025.xlsx into taio_pwt DB.
Creates ThisYearItem + Member + Item + Bid records for 收款台 support.

Usage:
    docker cp sorting2025.xlsx taio_pwt:/app/
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
from app.models.member import Member
from app.models.item import Item
from app.models.bid import Bid
import openpyxl


EXCEL_PATH = Path("/app/sorting2025.xlsx")


def safe_str(v):
    if v is None:
        return ""
    return str(v).strip()


def safe_float(v):
    if v is None:
        return 0.0
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def safe_int(v):
    if v is None:
        return 0
    try:
        return int(float(str(v).strip()))
    except (ValueError, TypeError):
        return 0


def get_or_create_member(name):
    """Find member by name, or create a stub member."""
    name = safe_str(name)
    if not name:
        return None
    member = Member.query.filter_by(name=name).first()
    if member:
        return member
    max_id = db.session.query(db.func.max(Member.member_id)).scalar() or 99
    member = Member(
        id=str(uuid.uuid4()),
        member_id=max_id + 1,
        name=name,
        member_type="member",
        status="active",
    )
    db.session.add(member)
    db.session.flush()
    print(f"  👤 Created member: {name} (#{member.member_id})")
    return member


def get_or_create_item(item_name, actual_item):
    """Find item by name_1_auspicious, or create new item master record."""
    item_name = safe_str(item_name) or safe_str(actual_item) or "未命名"
    actual_item = safe_str(actual_item)

    item = Item.query.filter_by(name_1_auspicious=item_name).first()
    if not item and actual_item:
        item = Item.query.filter_by(name_2_description=actual_item).first()
    if item:
        return item

    max_id = db.session.query(db.func.max(Item.item_id)).scalar() or 0
    item = Item(
        id=str(uuid.uuid4()),
        item_id=max_id + 1,
        name_1_auspicious=item_name,
        name_2_description=actual_item or None,
    )
    db.session.add(item)
    db.session.flush()
    print(f"  📦 Created item: {item_name} (ID#{item.item_id})")
    return item


def main():
    if not EXCEL_PATH.exists():
        print(f"❌ {EXCEL_PATH} not found! Copy it first:")
        print("   docker cp sorting2025.xlsx taio_pwt:/app/")
        return

    app = create_app()
    with app.app_context():
        db.create_all()

        print("=" * 60)
        print("📥 Importing 2025 sorting data...")
        print("=" * 60)

        wb = openpyxl.load_workbook(str(EXCEL_PATH), data_only=True)
        ws = wb["今年聖物2026"]

        # ── Column mapping ──
        # Col 1: 年份   → year
        # Col 2: 貼紙#  → sticker_no
        # Col 3: 聖物名稱 → item_name
        # Col 4: 實際物品 → actual_item
        # Col 5: 類別   → category
        # Col 6: 成本   → cost
        # Col 7: 來源   → source
        # Col 8: 投得者 → bidder_name + Member
        # Col 9: 競投金額 → bid_amount
        # Col 10: 經手人 → handler
        # Col 11: 相號  → photo_codes
        # Col 12: 備註  → notes

        stats = {"tyi": 0, "members": 0, "items": 0, "bids": 0}

        for r in range(2, ws.max_row + 1):
            year = safe_int(ws.cell(r, 1).value) or 2025
            sticker_no = safe_int(ws.cell(r, 2).value)
            item_name = safe_str(ws.cell(r, 3).value)
            actual_item = safe_str(ws.cell(r, 4).value)
            category = safe_str(ws.cell(r, 5).value)
            cost = safe_float(ws.cell(r, 6).value)
            source = safe_str(ws.cell(r, 7).value)
            bidder_name = safe_str(ws.cell(r, 8).value)
            bid_amount = safe_float(ws.cell(r, 9).value)
            handler = safe_str(ws.cell(r, 10).value)
            photo_codes = safe_str(ws.cell(r, 11).value)
            notes = safe_str(ws.cell(r, 12).value)

            if not item_name and not actual_item:
                continue

            # ── 1. Item master (for Bid.item_id FK) ──
            item = get_or_create_item(item_name, actual_item)
            stats["items"] += 1

            # ── 2. ThisYearItem ──
            tyi = ThisYearItem(
                year=year,
                sticker_no=sticker_no,
                item_name=item_name,
                actual_item=actual_item,
                category=category,
                cost=cost,
                source=source,
                bidder_name=bidder_name,
                bid_amount=bid_amount,
                paid_amount=0,
                handler=handler,
                photo_codes=photo_codes,
                notes=notes,
            )
            db.session.add(tyi)
            stats["tyi"] += 1

            # ── 3. Member + Bid (for 收款台) ──
            member = get_or_create_member(bidder_name)
            if member:
                stats["members"] += 1
                if bid_amount > 0:
                    bid = Bid(
                        id=str(uuid.uuid4()),
                        year=year,
                        bid_no=sticker_no,
                        item_id=item.item_id,
                        member_id=member.member_id,
                        bid_amount=bid_amount,
                        paid_amount=0,
                        handler=handler,
                        payment_method="cash",
                    )
                    db.session.add(bid)
                    stats["bids"] += 1

        db.session.commit()
        wb.close()

        print(f"\n✅ Import complete!")
        print(f"   ThisYearItems:    {stats['tyi']}")
        print(f"   Items (master):   {stats['items']} total (new + existing)")
        print(f"   Members:          {Member.query.count()} total")
        print(f"   Bids:             {stats['bids']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
