"""
寶榮堂花炮會管理系統 — SQLAlchemy Models Package.

All models import ``db`` from :mod:`app.extensions` and are registered
here so that ``create_app()`` can discover them via a single import.
"""

from app.extensions import db

# Core data models (from CSV imports)
from app.models.member import Member
from app.models.item import Item
from app.models.edition import Edition
from app.models.bid import Bid
from app.models.pl import PL

# Workflow / pre-event models
from app.models.this_year_item import ThisYearItem
from app.models.expense import Expense
from app.models.sponsor import Sponsor

# Live-event models
from app.models.live_income import LiveIncome
from app.models.live_expense import LiveExpense

# New feature models
from app.models.daily_entry import DailyEntry
from app.models.photo import Photo
from app.models.photo_link import PhotoLink

# Auth model
from app.models.user import User

__all__ = [
    "Member",
    "Item",
    "Edition",
    "Bid",
    "PL",
    "ThisYearItem",
    "Expense",
    "Sponsor",
    "LiveIncome",
    "LiveExpense",
    "DailyEntry",
    "Photo",
    "PhotoLink",
    "User",
]
