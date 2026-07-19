"""
Reset all transaction data for 寶榮堂花炮會管理系統.
Keeps: items, this_year_items (item data only), members, editions, users.
Clears: bids, live_income, live_expenses, expenses, membership_fees, sponsors, pl, daily_entries
Resets: this_year_items bid-related fields (bidder_name, bid_amount, handler, etc.)
"""
import sys
import os

# Add app to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db

app = create_app()

TABLES_TO_CLEAR = [
    "bids",
    "live_income",
    "live_expenses",
    "expenses",
    "membership_fees",
    "sponsors",
    "pl",
    "daily_entries",
]

THIS_YEAR_BID_FIELDS = {
    "bidder_name": None,
    "bid_amount": 0,
    "handler": "",
    "paid_amount": 0,
    "payment_method": "",
    "paid_handler": "",
    "photo_codes": "",
}

with app.app_context():
    print("🧹 Clearing transaction tables...")
    for table in TABLES_TO_CLEAR:
        db.session.execute(db.text(f"DELETE FROM {table}"))
        print(f"   ✅ {table} — cleared")

    print("\n🧹 Resetting bid fields in this_year_items...")
    for field, default in THIS_YEAR_BID_FIELDS.items():
        if default is None:
            db.session.execute(db.text(f"UPDATE this_year_items SET {field} = NULL"))
        elif isinstance(default, int):
            db.session.execute(db.text(f"UPDATE this_year_items SET {field} = 0"))
        else:
            db.session.execute(db.text(f"UPDATE this_year_items SET {field} = ''"))
    print(f"   ✅ this_year_items — {len(THIS_YEAR_BID_FIELDS)} fields reset")

    db.session.commit()
    print("\n🎉 Done! Transactions cleared, base data preserved.")
