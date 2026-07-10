"""Dashboard blueprint — main overview & statistics."""
from datetime import datetime

from flask import Blueprint, render_template, request
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models.bid import Bid
from app.models.edition import Edition
from app.models.expense import Expense
from app.models.member import Member
from app.models.sponsor import Sponsor
from app.models.this_year_item import ThisYearItem

bp = Blueprint("dashboard", __name__, template_folder="../templates/dashboard")


@bp.route("/")
@login_required
def dashboard():
    """Main dashboard — overview statistics for the current year."""
    year_str = request.args.get("year", str(datetime.now().year))
    year = int(year_str)

    # Basic counts
    members_count = Member.query.count()
    this_year_items_count = ThisYearItem.query.filter_by(year=year).count()

    # Sponsor total for current year
    sponsor_total = (
        db.session.query(func.coalesce(func.sum(Sponsor.amount), 0))
        .filter(Sponsor.year == year)
        .scalar()
    )

    # Pre-event expenses for current year
    expenses_total = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0))
        .filter(Expense.year == year, Expense.source == "pre")
        .scalar()
    )

    # Unpaid bids from previous year
    prev_year = year - 1
    prev_unpaid = Bid.query.filter(
        Bid.year == prev_year, Bid.paid_amount == 0, Bid.bid_amount > 0
    ).count()

    # NEW: 競投總額(本年) — total bid amount for current year
    bid_total = (
        db.session.query(func.coalesce(func.sum(Bid.bid_amount), 0))
        .filter(Bid.year == year, Bid.bid_amount > 0)
        .scalar()
    )

    # NEW: 已收金額(本年) — total paid amount for current year
    paid_total = (
        db.session.query(func.coalesce(func.sum(Bid.paid_amount), 0))
        .filter(Bid.year == year)
        .scalar()
    )

    # NEW: 未收金額(本年) — unpaid balance for current year
    unpaid_total = bid_total - paid_total

    stats = {
        "members": members_count,
        "this_year_items": this_year_items_count,
        "prev_unpaid": prev_unpaid,
        "sponsors": sponsor_total,
        "expenses": expenses_total,
        "bid_total": bid_total,
        "paid_total": paid_total,
        "unpaid_total": unpaid_total,
    }

    return render_template("dashboard.html", stats=stats, year=year)
