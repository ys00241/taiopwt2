#!/usr/bin/env python3
"""
Import 2025 sorting data (sorting2025.xlsx) into taio_pwt DB.
Maps Excel columns to ThisYearItem + Bid + Item + Member models.

Usage:
    docker cp sorting2025.xlsx taio_pwt:/app/
    docker exec taio_pwt python scripts/import_2025.py
"""
import sys
import os
import uuid
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("FLASK_ENV", "production")

from app import create_app
from app.extensions import db
from app.models.member import Member
from app.models.item import Item
from app.models.this_year_item import ThisYearItem
from app.models.bid import Bid
from app.models.edition import Edition
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


def get_or_create_item(name_1, name_2):
    """Find item by name_1_auspicious, or create new item master record."""
    name_1 = safe_str(name_1) or safe_str(name_2) or "未命名"
    name_2 = safe_str(name_2)

    item = Item.query.filter_by(name_1_auspicious=name_1).first()
    if not item and name_2:
        item = Item.query.filter_by(name_2_description=name_2).first()
    if item:
        return item

    max_id = db.session.query(db.func.max(Item.item_id)).scalar() or 0
    item = Item(
        item_id=max_id + 1,
        name_1_auspicious=name_1,
        name_2_description=name_2 or None,
    )
    db.session.add(item)
    db.session.flush()
    print(f"  📦 Created item: {name_1} (ID#{item.item_id})")
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

        # ── Column mapping (Excel col → DB field) ──
        # Col 1: 年份 → year
        # Col 2: 貼紙# → sticker_no
        # Col 3: 聖物名稱 → item_name / Item.name_1_auspicious
        # Col 4: 實際物品 → actual_item / Item.name_2_description
        # Col 5: 類別 → category
        # Col 6: 成本 → cost
        # Col 7: 來源 → source
        # Col 8: 投得者 → bidder_name / Member.name
        # Col 9: 競投金額 → bid_amount
        # Col 10: 經手人 → handler
        # Col 11: 相號 → photo_codes
        # Col 12: 備註 → notes

        stats = {"items": 0, "this_year": 0, "bids": 0, "members": 0}

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
                continue  # skip truly empty rows

            # ── 1. Item Master ──
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
            stats["this_year"] += 1

            # ── 3. Member + Bid ──
            member = get_or_create_member(bidder_name)
            if member and bid_amount > 0:
                stats["members"] += 1
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

        # ── 4. Edition 2025 ──
        if not Edition.query.filter_by(year=2025).first():
            db.session.add(Edition(
                id=str(uuid.uuid4()),
                year=2025,
                edition_no=1,
                event_date="2025-03-01",
                status="completed",
            ))

        db.session.commit()
        wb.close()

        print("\n" + "=" * 60)
        print("✅ Import complete!")
        print(f"   Items master:     {stats['items']}")
        print(f"   ThisYearItems:    {stats['this_year']}")
        print(f"   Members created:  {Member.query.count()}")
        print(f"   Bids created:     {stats['bids']}")
        print("=" * 60)


if __name__ == "__main__":
    main()
