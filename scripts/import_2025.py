#!/usr/bin/env python3
"""
Import 2025 sorting data from sorting2025.xlsx into taio_pwt DB.
Each Excel row → one ThisYearItem record (direct field mapping).

Usage:
    docker cp sorting2025.xlsx taio_pwt:/app/
    docker exec taio_pwt python scripts/import_2025.py
"""
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("FLASK_ENV", "production")

from app import create_app
from app.extensions import db
from app.models.this_year_item import ThisYearItem
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
        # Col 1: 年份   → year
        # Col 2: 貼紙#  → sticker_no
        # Col 3: 聖物名稱 → item_name
        # Col 4: 實際物品 → actual_item
        # Col 5: 類別   → category
        # Col 6: 成本   → cost
        # Col 7: 來源   → source
        # Col 8: 投得者 → bidder_name
        # Col 9: 競投金額 → bid_amount
        # Col 10: 經手人 → handler
        # Col 11: 相號  → photo_codes
        # Col 12: 備註  → notes

        count = 0

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
                continue  # skip empty rows

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
            count += 1

        db.session.commit()
        wb.close()

        print(f"\n✅ Import complete! {count} records added to this_year_items (2025).")
        print("=" * 60)


if __name__ == "__main__":
    main()
