"""API blueprint — RESTful JSON endpoints for AJAX and live dashboard."""
from flask import Blueprint
from flask_login import login_required

bp = Blueprint("api", __name__, template_folder="../templates/api")


@bp.route("/live/stats")
@login_required
def live_stats():
    """Return real-time stats for the live dashboard as JSON."""
    from flask import jsonify, request
    from app.extensions import db
    from app.models.edition import Edition
    from app.models.this_year_item import ThisYearItem
    from app.models.live_income import LiveIncome
    from app.models.live_expense import LiveExpense
    from app.models.bid import Bid
    from sqlalchemy import func

    year = request.args.get("year", type=int)
    if not year:
        year = db.session.query(func.max(Edition.year)).scalar() or 2025

    # Counts
    item_count = ThisYearItem.query.filter(ThisYearItem.year == year).count()
    bid_count = Bid.query.filter(Bid.year == year).count()

    # Items with bidders (paid or not)
    items_with_bids = (
        db.session.query(ThisYearItem)
        .filter(ThisYearItem.year == year, ThisYearItem.bidder_name != "", ThisYearItem.bid_amount > 0)
        .count()
    )
    items_remaining = item_count - items_with_bids

    # Income / Expense
    total_income = (
        db.session.query(func.coalesce(func.sum(LiveIncome.amount), 0))
        .filter(LiveIncome.year == year)
        .scalar()
    ) or 0

    total_expense = (
        db.session.query(func.coalesce(func.sum(LiveExpense.amount), 0))
        .filter(LiveExpense.year == year)
        .scalar()
    ) or 0

    # Payment method breakdown
    income_by_method = (
        db.session.query(LiveIncome.payment_method, func.sum(LiveIncome.amount))
        .filter(LiveIncome.year == year)
        .group_by(LiveIncome.payment_method)
        .all()
    )

    return jsonify({
        "year": year,
        "ok": True,
        "stats": {
            "items_total": item_count,
            "items_with_bids": items_with_bids,
            "items_remaining": items_remaining,
            "total_bids": bid_count,
            "total_income": float(total_income),
            "total_expense": float(total_expense),
            "net": float(total_income - total_expense),
            "income_by_method": [
                {"method": m or "N/A", "amount": float(a or 0)}
                for m, a in income_by_method
            ],
        },
    })


@bp.route("/items/<int:item_id>/bidders")
@login_required
def item_bidders(item_id):
    """Return list of bidders for a given item as JSON."""
    from flask import jsonify
    from app.extensions import db
    from app.models.bid import Bid
    from app.models.member import Member

    bids = (
        Bid.query.options(db.joinedload(Bid.member))
        .filter(Bid.item_id == item_id)
        .order_by(Bid.bid_amount.desc())
        .all()
    )

    return jsonify({
        "ok": True,
        "item_id": item_id,
        "bidders": [
            {
                "bid_id": b.id,
                "member_id": b.member.member_id if b.member else None,
                "member_name": b.member.name if b.member else "",
                "bid_amount": b.bid_amount or 0,
                "paid_amount": b.paid_amount or 0,
                "payment_method": b.payment_method or "",
                "handler": b.handler or "",
                "phone": b.member.phone if b.member else "",
            }
            for b in bids
        ],
    })


@bp.route("/items/<int:item_id>/detail")
@login_required
def item_detail(item_id):
    """Return item detail with bid summary as JSON."""
    from flask import jsonify
    from app.extensions import db
    from app.models.item import Item
    from app.models.bid import Bid
    from sqlalchemy import func

    item = Item.query.filter(Item.item_id == item_id).first()
    if not item:
        return jsonify({"ok": False, "error": "Item not found"}), 404

    bid_stats = (
        db.session.query(
            func.count(Bid.id),
            func.sum(Bid.bid_amount),
            func.sum(Bid.paid_amount),
        )
        .filter(Bid.item_id == item_id)
        .first()
    )

    return jsonify({
        "ok": True,
        "item": {
            "item_id": item.item_id,
            "name_1_auspicious": item.name_1_auspicious or "",
            "name_2_description": item.name_2_description or "",
            "year_data": item.year_data,
        },
        "bid_stats": {
            "total_bids": bid_stats[0] or 0,
            "total_bid_amount": float(bid_stats[1] or 0),
            "total_paid_amount": float(bid_stats[2] or 0),
        },
    })


@bp.route("/editions/<int:edition_id>/data")
@login_required
def edition_data(edition_id):
    """Return full edition (year) data as JSON — summary of all records."""
    from flask import jsonify
    from app.extensions import db
    from app.models.edition import Edition
    from app.models import (
        Member, Item, Bid, PL, ThisYearItem, Expense,
        Sponsor, LiveIncome, LiveExpense, DailyEntry,
    )
    from sqlalchemy import func

    edition = Edition.query.filter(Edition.edition_id == edition_id).first()
    if not edition:
        return jsonify({"ok": False, "error": "Edition not found"}), 404

    year = edition.year

    # Aggregate counts and sums for the year
    member_count = Member.query.count()  # all members, not year-specific

    item_count = ThisYearItem.query.filter(ThisYearItem.year == year).count()
    bid_count = Bid.query.filter(Bid.year == year).count()
    bid_total = (
        db.session.query(func.coalesce(func.sum(Bid.bid_amount), 0))
        .filter(Bid.year == year)
        .scalar()
    ) or 0

    income_total = (
        db.session.query(func.coalesce(func.sum(LiveIncome.amount), 0))
        .filter(LiveIncome.year == year)
        .scalar()
    ) or 0

    expense_count = (
        Expense.query.filter(Expense.year == year).count()
        + LiveExpense.query.filter(LiveExpense.year == year).count()
    )
    expense_total = (
        db.session.query(func.coalesce(func.sum(Expense.amount), 0) +
                         func.coalesce(func.sum(LiveExpense.amount), 0))
        .select_from(Expense)
        .filter(Expense.year == year)
        .scalar()
    ) or 0

    # Also get live_expense total
    live_expense_total = (
        db.session.query(func.coalesce(func.sum(LiveExpense.amount), 0))
        .filter(LiveExpense.year == year)
        .scalar()
    ) or 0

    # PL entries
    pl_entries = PL.query.filter(PL.year == year).count()

    sponsor_total = (
        db.session.query(func.coalesce(func.sum(Sponsor.amount), 0))
        .filter(Sponsor.year == year)
        .scalar()
    ) or 0

    daily_count = DailyEntry.query.filter(DailyEntry.year == year).count()

    return jsonify({
        "ok": True,
        "edition": {
            "edition_id": edition.edition_id,
            "edition_no": edition.edition_no,
            "year": edition.year,
            "event_date": edition.event_date or "",
            "venue": edition.venue or "",
            "tables": edition.tables or 0,
            "singer": edition.singer or "",
            "member_count": edition.member_count or 0,
            "remarks": edition.remarks or "",
        },
        "summary": {
            "total_members": member_count,
            "items_count": item_count,
            "bids_count": bid_count,
            "bids_total_amount": float(bid_total),
            "income_total": float(income_total),
            "expense_count": expense_count,
            "expense_total": float(expense_total + live_expense_total),
            "pl_entries": pl_entries,
            "sponsor_total": float(sponsor_total),
            "daily_entries": daily_count,
        },
    })


@bp.route("/categories")
@login_required
def api_categories():
    """Return expense categories as JSON (distinct categories from Expense table)."""
    from flask import jsonify, request
    from app.extensions import db
    from app.models.expense import Expense
    from app.models.edition import Edition
    from sqlalchemy import func

    year = request.args.get("year", type=int)
    if not year:
        year = db.session.query(func.max(Edition.year)).scalar() or 2025

    categories = (
        db.session.query(Expense.category)
        .filter(Expense.year == year, Expense.category != "")
        .distinct()
        .order_by(Expense.category)
        .all()
    )

    return jsonify({
        "ok": True,
        "year": year,
        "categories": [c[0] for c in categories],
    })


# Keep the original search endpoint too
@bp.route("/search")
@login_required
def api_search():
    """Universal search endpoint."""
    from flask import jsonify
    return jsonify({"ok": True, "results": []})
