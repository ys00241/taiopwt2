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

bp = Blueprint("dashboard", __name__)


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

    # 競投總額(本年) — query ThisYearItem (NOT Bid, since Bid may be empty)
    bid_total = (
        db.session.query(func.coalesce(func.sum(ThisYearItem.bid_amount), 0))
        .filter(ThisYearItem.year == year, ThisYearItem.bid_amount > 0)
        .scalar()
    )

    # 已收金額(本年) — paid_amount on this_year_items + live_income
    paid_in_items = (
        db.session.query(func.coalesce(func.sum(ThisYearItem.paid_amount), 0))
        .filter(ThisYearItem.year == year, ThisYearItem.paid_amount > 0)
        .scalar()
    )
    from app.models.live_income import LiveIncome
    live_collected = (
        db.session.query(func.coalesce(func.sum(LiveIncome.amount), 0))
        .filter(LiveIncome.source_year == year)
        .scalar()
    )
    paid_total = paid_in_items + live_collected

    # 未收金額(本年)
    unpaid_total = bid_total - paid_total

    # Recent bids — from ThisYearItem directly (not Bid)
    recent_bids_data = (
        ThisYearItem.query
        .filter(ThisYearItem.year == year, ThisYearItem.bidder_name != "", ThisYearItem.bid_amount > 0)
        .order_by(ThisYearItem.sticker_no)
        .limit(10)
        .all()
    )
    recent_bids = []
    for tyi in recent_bids_data:
        recent_bids.append({
            "member_name": tyi.bidder_name,
            "item_name": tyi.item_name,
            "bid_amount": tyi.bid_amount,
            "paid_amount": tyi.paid_amount,
        })

    # Upcoming events — from Edition
    upcoming_q = Edition.query.filter(
        Edition.year >= datetime.now().year
    ).order_by(Edition.year).limit(5).all()
    upcoming_events = []
    for ed in upcoming_q:
        upcoming_events.append({
            "day": ed.event_date[-2:] if ed.event_date and len(ed.event_date) >= 2 else str(ed.year),
            "month": f"{ed.year}年",
            "title": f"第{ed.edition_no or '?'}屆花炮會",
            "description": ed.venue or "",
        })

    # Available years for selector
    years = [r[0] for r in
        db.session.query(ThisYearItem.year)
        .distinct()
        .order_by(ThisYearItem.year.desc())
        .all()
    ]
    if not years:
        years = [datetime.now().year]

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

    return render_template(
        "dashboard/dashboard.html",
        stats=stats,
        year=year,
        years=years,
        recent_bids=recent_bids,
        upcoming_events=upcoming_events,
    )
