"""Live-event blueprint — 現場活動 (競投台, 收款台, 現場收支, 實時儀錶板), mobile-optimized."""
from io import BytesIO
from datetime import datetime

from flask import (
    Blueprint, render_template, request, jsonify, send_file,
)
from flask_login import login_required

from app.extensions import db
from app.models.this_year_item import ThisYearItem
from app.models.bid import Bid
from app.models.member import Member
from app.models.live_income import LiveIncome
from app.models.expense import Expense
from app.models.edition import Edition

bp = Blueprint("live_event", __name__,
               url_prefix="/live")


# ════════════════════════════════════════════════════════════════════════
#  A) 競投台 — Bidding
# ════════════════════════════════════════════════════════════════════════

@bp.route("/bidding")
@login_required
def live_bidding():
    """競投台 — List available/won items + members for autocomplete."""
    year = request.args.get("year", datetime.now().strftime("%Y"))
    items = (
        ThisYearItem.query
        .filter_by(year=int(year))
        .order_by(ThisYearItem.sticker_no)
        .all()
    )
    # Available items (not yet won)
    available = [item for item in items if not item.bidder_name]
    # Won items
    won = [item for item in items if item.bidder_name]

    # Members for autocomplete
    members = Member.query.order_by(Member.name).all()

    # Available years
    years = [
        r[0] for r in
        db.session.query(ThisYearItem.year)
        .distinct()
        .order_by(ThisYearItem.year.desc())
        .all()
    ]

    # Stats for template
    stats = {
        "bid_total": sum((i.bid_amount or 0) for i in won),
        "won_count": len(won),
        "available_count": len(available),
    }

    return render_template(
        "live_event/bidding.html",
        available=available, won=won,
        items_all=items,
        members=members,
        years=years,
        year=year,
        stats=stats,
    )


@bp.route("/bidding/record", methods=["POST"])
@login_required
def live_bidding_record():
    """Record a bid (update this_year_items)."""
    item_id = int(request.form.get("item_id", 0))
    bidder_name = request.form.get("bidder_name", "").strip()
    bid_amount = float(request.form.get("bid_amount", 0) or 0)
    handler = request.form.get("handler", "").strip()
    photo_codes = request.form.get("photo_codes", "").strip()
    paid_amount = float(request.form.get("paid_amount", 0) or 0)
    payment_method = request.form.get("payment_method", "")
    paid_handler = request.form.get("paid_handler", "").strip()

    item = db.session.get(ThisYearItem, item_id)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    item.bidder_name = bidder_name
    item.bid_amount = bid_amount
    item.handler = handler
    item.photo_codes = photo_codes
    item.paid_amount = paid_amount
    item.payment_method = payment_method if paid_amount > 0 else item.payment_method
    item.paid_handler = paid_handler if paid_amount > 0 else item.paid_handler

    db.session.commit()
    return jsonify({"ok": True})


# ════════════════════════════════════════════════════════════════════════
#  B) 收款台 — Payments
# ════════════════════════════════════════════════════════════════════════

@bp.route("/payments")
@login_required
def live_payments():
    """收款台 — Search members, show debt + recent payments."""
    year = request.args.get("year", datetime.now().strftime("%Y"))
    int_year = int(year)
    source_year = request.args.get("sy", "").strip()
    search = request.args.get("q", "").strip()
    int_source_year = int(source_year) if source_year else None

    # Build member debt query
    if int_source_year:
        # Scope to a specific source year
        total_due_sub = (
            db.session.query(db.func.coalesce(db.func.sum(Bid.bid_amount), 0))
            .filter(
                Bid.member_id == Member.member_id,
                Bid.year == int_source_year,
                Bid.bid_amount > 0,
            )
            .scalar_subquery()
        )
        total_paid_sub = (
            db.session.query(db.func.coalesce(db.func.sum(Bid.paid_amount), 0))
            .filter(
                Bid.member_id == Member.member_id,
                Bid.year == int_source_year,
            )
            .scalar_subquery()
        )
        live_paid_sub = (
            db.session.query(db.func.coalesce(db.func.sum(LiveIncome.amount), 0))
            .filter(
                LiveIncome.member_id == Member.member_id,
                LiveIncome.source_year == int_source_year,
                LiveIncome.year == int_year,
            )
            .scalar_subquery()
        )

        members_q = (
            db.session.query(
                Member.member_id,
                Member.name,
                total_due_sub.label("total_due"),
                total_paid_sub.label("total_paid"),
                live_paid_sub.label("live_paid"),
            )
            .filter(Member.member_id.in_(
                db.session.query(Bid.member_id)
                .filter(Bid.year == int_source_year, Bid.bid_amount > 0)
                .distinct()
            ))
        )
    else:
        total_due_sub = (
            db.session.query(db.func.coalesce(db.func.sum(Bid.bid_amount), 0))
            .filter(
                Bid.member_id == Member.member_id,
                Bid.bid_amount > 0,
            )
            .scalar_subquery()
        )
        total_paid_sub = (
            db.session.query(db.func.coalesce(db.func.sum(Bid.paid_amount), 0))
            .filter(Bid.member_id == Member.member_id)
            .scalar_subquery()
        )
        live_paid_sub = (
            db.session.query(db.func.coalesce(db.func.sum(LiveIncome.amount), 0))
            .filter(
                LiveIncome.member_id == Member.member_id,
                LiveIncome.year == int_year,
            )
            .scalar_subquery()
        )

        members_q = (
            db.session.query(
                Member.member_id,
                Member.name,
                total_due_sub.label("total_due"),
                total_paid_sub.label("total_paid"),
                live_paid_sub.label("live_paid"),
            )
            .filter(Member.member_id.in_(
                db.session.query(Bid.member_id)
                .filter(Bid.bid_amount > 0)
                .distinct()
            ))
        )

    rows = members_q.all()
    result = []
    for r in rows:
        d = r._asdict()
        due = d["total_due"] or 0
        paid = (d["total_paid"] or 0) + (d["live_paid"] or 0)
        d["total_paid_combined"] = paid
        d["unpaid"] = due - paid
        result.append(d)

    # Search filter
    if search:
        name_match_ids = {
            r["member_id"] for r in result
            if search.lower() in (r["name"] or "").lower()
        }
        # Also search by item name in this_year_items (bidders)
        if int_source_year:
            item_matches = (
                db.session.query(ThisYearItem.bidder_name)
                .filter(
                    ThisYearItem.year == int_source_year,
                    ThisYearItem.item_name.ilike(f"%{search}%"),
                    ThisYearItem.bidder_name.isnot(None),
                    ThisYearItem.bidder_name != "",
                )
                .all()
            )
            hist_matches = (
                db.session.query(Bid.member_id)
                .join(Bid.item, isouter=True)
                .filter(
                    Bid.year == int_source_year,
                    db.or_(
                        Bid.item.has(db.or_(
                            Bid.item.name_1_auspicious.ilike(f"%{search}%"),
                            Bid.item.name_2_description.ilike(f"%{search}%"),
                        ))
                    ),
                )
                .distinct()
                .all()
            )
        else:
            item_matches = (
                db.session.query(ThisYearItem.bidder_name)
                .filter(
                    ThisYearItem.item_name.ilike(f"%{search}%"),
                    ThisYearItem.bidder_name.isnot(None),
                    ThisYearItem.bidder_name != "",
                )
                .all()
            )
            hist_matches = (
                db.session.query(Bid.member_id)
                .join(Bid.item, isouter=True)
                .filter(
                    db.or_(
                        Bid.item.has(db.or_(
                            Bid.item.name_1_auspicious.ilike(f"%{search}%"),
                            Bid.item.name_2_description.ilike(f"%{search}%"),
                        ))
                    ),
                )
                .distinct()
                .all()
            )
        item_match_names = {r[0] for r in item_matches if r[0]}
        hist_match_ids = {r[0] for r in hist_matches}
        result = [
            r for r in result
            if r["member_id"] in name_match_ids
               or r["member_id"] in hist_match_ids
               or r["name"] in item_match_names
        ]

    # Recent payments
    if int_source_year:
        recent = (
            LiveIncome.query
            .filter_by(year=int_year, source_year=int_source_year)
            .order_by(LiveIncome.id.desc())
            .limit(20)
            .all()
        )
    else:
        recent = (
            LiveIncome.query
            .filter_by(year=int_year)
            .order_by(LiveIncome.id.desc())
            .limit(50)
            .all()
        )

    # Available years for dropdown
    years = [
        r[0] for r in
        db.session.query(Bid.year)
        .distinct()
        .order_by(Bid.year.desc())
        .all()
    ]

    return render_template(
        "live_event/payments.html",
        members=result, recent=recent,
        year=year, source_year=source_year, search=search,
        years=years,
    )


@bp.route("/payments/pay", methods=["POST"])
@login_required
def live_payments_pay():
    """Record a payment + auto-distribute across unpaid bids (FIFO)."""
    year = int(request.form.get("year", datetime.now().strftime("%Y")))
    member_id = int(request.form.get("member_id", 0))
    member_name = request.form.get("member_name", "")
    source_year = int(request.form.get("source_year", year - 1))
    amount = float(request.form.get("amount", 0) or 0)
    payment_method = request.form.get("payment_method", "CASH")
    handler = request.form.get("handler", "")
    remarks = request.form.get("remarks", "")

    # Record payment in live_income
    income = LiveIncome(
        year=year,
        member_id=member_id,
        member_name=member_name,
        source_year=source_year,
        amount=amount,
        payment_method=payment_method,
        handler=handler,
        remarks=remarks,
    )
    db.session.add(income)

    # Distribute payment across unpaid bids (FIFO: oldest bid_no first)
    unpaid_bids = (
        Bid.query
        .filter(
            Bid.member_id == member_id,
            Bid.year == source_year,
            Bid.bid_amount > Bid.paid_amount,
        )
        .order_by(Bid.bid_no)
        .all()
    )

    remaining = amount
    for bid in unpaid_bids:
        if remaining <= 0:
            break
        bid_paid = bid.paid_amount or 0
        bid_total = bid.bid_amount or 0
        outstanding = bid_total - bid_paid
        to_pay = min(remaining, outstanding)
        bid.paid_amount = (bid.paid_amount or 0) + to_pay
        bid.payment_method = payment_method
        bid.handler = handler
        remaining -= to_pay

    db.session.commit()

    return jsonify({
        "ok": True,
        "paid": amount,
        "remaining": max(0, remaining),
    })


# ════════════════════════════════════════════════════════════════════════
#  C) 收入管理 — Live income CRUD
# ════════════════════════════════════════════════════════════════════════

@bp.route("/income")
@login_required
def live_income():
    """現場收款列表 — Live income list + total."""
    year = request.args.get("year", datetime.now().strftime("%Y"))
    items = (
        LiveIncome.query
        .filter_by(year=int(year))
        .order_by(LiveIncome.id.desc())
        .limit(50)
        .all()
    )
    total = (
        db.session.query(db.func.coalesce(db.func.sum(LiveIncome.amount), 0))
        .filter(LiveIncome.year == int(year))
        .scalar()
    )
    return render_template("live_event/live_income.html", items=items, year=year, total=total)


@bp.route("/income/<int:iid>/edit", methods=["POST"])
@login_required
def live_income_edit(iid):
    """Edit a live income record."""
    income = db.session.get(LiveIncome, iid)
    if not income:
        return jsonify({"error": "Income record not found"}), 404

    income.member_name = request.form.get("member_name", income.member_name)
    income.amount = float(request.form.get("amount", 0) or 0)
    income.payment_method = request.form.get("payment_method", income.payment_method)
    income.handler = request.form.get("handler", income.handler)
    income.remarks = request.form.get("remarks", income.remarks)
    src_yr = request.form.get("source_year")
    if src_yr:
        income.source_year = int(src_yr)

    # Also update member_id if provided
    mid = request.form.get("member_id")
    if mid:
        income.member_id = int(mid)

    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/income/<int:iid>/delete", methods=["POST"])
@login_required
def live_income_delete(iid):
    """Delete a live income record."""
    income = db.session.get(LiveIncome, iid)
    if not income:
        return jsonify({"error": "Income record not found"}), 404
    db.session.delete(income)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/expenses_live")
@login_required
def live_expenses_live():
    """現場支出列表 — Live expenses list + total."""
    year = request.args.get("year", datetime.now().strftime("%Y"))
    items = (
        Expense.query
        .filter_by(year=int(year), source="live")
        .order_by(Expense.id.desc())
        .limit(50)
        .all()
    )
    total = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0))
        .filter(Expense.year == int(year), Expense.source == "live")
        .scalar()
    )
    return render_template("live_event/live_expenses.html", items=items, year=year, total=total)


@bp.route("/expenses_live/add", methods=["POST"])
@login_required
def live_expenses_live_add():
    """Add a live expense."""
    year = int(request.form.get("year", datetime.now().strftime("%Y")))
    expense = Expense(
        year=year,
        source="live",
        subject=request.form.get("subject", ""),
        amount=float(request.form.get("amount", 0) or 0),
        payment_method=request.form.get("payment_method", ""),
        handler=request.form.get("handler", ""),
        details=request.form.get("details", ""),
    )
    db.session.add(expense)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/expenses_live/<int:eid>/edit", methods=["POST"])
@login_required
def live_expenses_live_edit(eid):
    """Edit a live expense."""
    expense = db.session.get(Expense, eid)
    if not expense or expense.source != "live":
        return jsonify({"error": "Expense not found"}), 404
    expense.subject = request.form.get("subject", expense.subject)
    expense.amount = float(request.form.get("amount", 0) or 0)
    expense.payment_method = request.form.get("payment_method", expense.payment_method)
    expense.handler = request.form.get("handler", expense.handler)
    expense.details = request.form.get("details", expense.details)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/expenses_live/<int:eid>/delete", methods=["POST"])
@login_required
def live_expenses_live_delete(eid):
    """Delete a live expense."""
    expense = db.session.get(Expense, eid)
    if not expense or expense.source != "live":
        return jsonify({"error": "Expense not found"}), 404
    db.session.delete(expense)
    db.session.commit()
    return jsonify({"ok": True})


# ════════════════════════════════════════════════════════════════════════
#  D) 現場儀錶板 — Live Dashboard
# ════════════════════════════════════════════════════════════════════════

@bp.route("/dashboard")
@login_required
def live_dashboard():
    """現場儀錶板 — Real-time stats page."""
    year_str = request.args.get("year", datetime.now().strftime("%Y"))
    year = int(year_str)
    prev_year = year - 1

    # Previous year unpaid stats
    prev_unpaid = (
        db.session.query(
            db.func.count(Bid.id).label("cnt"),
            db.func.coalesce(db.func.sum(Bid.bid_amount - Bid.paid_amount), 0).label("total"),
        )
        .filter(Bid.year == prev_year, Bid.bid_amount > Bid.paid_amount)
        .first()
    )
    prev_paid = (
        db.session.query(
            db.func.count(Bid.id).label("cnt"),
            db.func.coalesce(db.func.sum(Bid.paid_amount), 0).label("total"),
        )
        .filter(Bid.year == prev_year, Bid.paid_amount > 0)
        .first()
    )

    # This year's live collections
    live_collected = (
        db.session.query(db.func.coalesce(db.func.sum(LiveIncome.amount), 0))
        .filter(LiveIncome.year == year)
        .scalar()
    )

    # This year's bidding stats
    bid_stats = (
        db.session.query(
            db.func.count(ThisYearItem.id).label("cnt"),
            db.func.coalesce(db.func.sum(ThisYearItem.bid_amount), 0).label("total"),
            db.func.coalesce(db.func.max(ThisYearItem.bid_amount), 0).label("highest"),
            db.func.coalesce(db.func.avg(ThisYearItem.bid_amount), 0).label("avg"),
        )
        .filter(ThisYearItem.year == year, ThisYearItem.bid_amount > 0)
        .first()
    )

    # Highest bid item
    top_item = (
        ThisYearItem.query
        .filter(ThisYearItem.year == year, ThisYearItem.bid_amount > 0)
        .order_by(ThisYearItem.bid_amount.desc())
        .first()
    )

    # Expenses
    total_pre_expenses = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0))
        .filter(Expense.year == year, Expense.source == "pre")
        .scalar()
    )
    total_live_expenses = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0))
        .filter(Expense.year == year, Expense.source == "live")
        .scalar()
    )

    # Items not yet won
    items_left = (
        ThisYearItem.query
        .filter(
            ThisYearItem.year == year,
            db.or_(
                ThisYearItem.bidder_name.is_(None),
                ThisYearItem.bidder_name == "",
            ),
        )
        .count()
    )

    # Sponsors total
    sponsors_total = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0))
        .filter(Expense.year == year)
        .scalar()
    )

    # Build stats dict for template
    top_bidder_name = top_item.bidder_name if top_item else None
    total_items_count = ThisYearItem.query.filter(ThisYearItem.year == year).count()

    stats_dict = {
        "bid_total": bid_stats.total or 0,
        "paid_total": live_collected or 0,
        "remaining_items": items_left or 0,
        "total_items": total_items_count,
        "live_expenses": total_live_expenses or 0,
        "highest_bid": bid_stats.highest or 0,
        "highest_bidder": top_bidder_name,
    }

    return render_template(
        "live_event/dashboard.html",
        year=year_str, prev_year=str(prev_year),
        prev_unpaid={"cnt": prev_unpaid.cnt or 0, "total": prev_unpaid.total or 0},
        prev_paid={"cnt": prev_paid.cnt or 0, "total": prev_paid.total or 0},
        live_collected=live_collected or 0,
        stats=stats_dict,
        top_item=top_item,
        total_expenses=(total_pre_expenses or 0) + (total_live_expenses or 0),
        total_pre_expenses=total_pre_expenses or 0,
        live_exp=total_live_expenses or 0,
        stats_items_left=items_left,
        sponsors_total=sponsors_total or 0,
    )


# ════════════════════════════════════════════════════════════════════════
#  API: Live stats (for real-time AJAX refresh)
# ════════════════════════════════════════════════════════════════════════

@bp.route("/stats")
def live_stats_api():
    """Return live stats as JSON for real-time dashboard updates."""
    year = int(request.args.get("year", datetime.now().strftime("%Y")))
    prev_year = year - 1

    prev_unpaid = (
        db.session.query(
            db.func.count(Bid.id).label("cnt"),
            db.func.coalesce(db.func.sum(Bid.bid_amount - Bid.paid_amount), 0).label("total"),
        )
        .filter(Bid.year == prev_year, Bid.bid_amount > Bid.paid_amount)
        .first()
    )

    live_collected = (
        db.session.query(db.func.coalesce(db.func.sum(LiveIncome.amount), 0))
        .filter(LiveIncome.year == year)
        .scalar()
    )

    bid_stats = (
        db.session.query(
            db.func.count(ThisYearItem.id).label("cnt"),
            db.func.coalesce(db.func.sum(ThisYearItem.bid_amount), 0).label("total"),
            db.func.coalesce(db.func.max(ThisYearItem.bid_amount), 0).label("highest"),
        )
        .filter(ThisYearItem.year == year, ThisYearItem.bid_amount > 0)
        .first()
    )

    expenses = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0))
        .filter(Expense.year == year, Expense.source == "pre")
        .scalar()
    )
    live_exp = (
        db.session.query(db.func.coalesce(db.func.sum(Expense.amount), 0))
        .filter(Expense.year == year, Expense.source == "live")
        .scalar()
    )

    items_left = (
        ThisYearItem.query
        .filter(
            ThisYearItem.year == year,
            db.or_(
                ThisYearItem.bidder_name.is_(None),
                ThisYearItem.bidder_name == "",
            ),
        )
        .count()
    )

    prev_paid_members = (
        db.session.query(db.func.count(db.func.distinct(Bid.member_id)))
        .filter(Bid.year == prev_year, Bid.paid_amount > 0)
        .scalar()
    )

    return jsonify({
        "prev_unpaid_cnt": prev_unpaid.cnt if prev_unpaid else 0,
        "prev_unpaid_total": prev_unpaid.total if prev_unpaid else 0,
        "prev_paid_items": prev_paid_members or 0,
        "live_collected": live_collected or 0,
        "bid_cnt": bid_stats.cnt if bid_stats else 0,
        "bid_total": bid_stats.total if bid_stats else 0,
        "bid_highest": bid_stats.highest if bid_stats else 0,
        "items_left": items_left,
        "expenses": (expenses or 0) + (live_exp or 0),
    })
