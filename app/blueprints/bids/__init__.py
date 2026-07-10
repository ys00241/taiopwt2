"""Bids blueprint — 投標記錄列表與CSV匯出."""
from flask import Blueprint
from flask_login import login_required

bp = Blueprint("bids", __name__, template_folder="../templates/bids")


@bp.route("/bids")
@login_required
def list_bids():
    """List bids with optional year filter and search (by member name / item name)."""
    from flask import render_template, request
    from app.extensions import db
    from app.models.bid import Bid
    from app.models.member import Member
    from app.models.item import Item
    from app.models.edition import Edition
    from sqlalchemy import func

    year = request.args.get("year", type=int)
    search = request.args.get("search", "").strip()

    # Default to latest available year
    if not year:
        latest = db.session.query(func.max(Edition.year)).scalar()
        year = latest or 2025

    # Build query with eager-loaded relationships
    query = Bid.query.options(
        db.joinedload(Bid.member),
        db.joinedload(Bid.item),
    ).filter(Bid.year == year)

    if search:
        pattern = f"%{search}%"
        query = query.join(Bid.member).join(Bid.item, isouter=True).filter(
            db.or_(
                Member.name.ilike(pattern),
                Item.name_1_auspicious.ilike(pattern),
                Item.name_2_description.ilike(pattern),
            )
        )

    bids = query.order_by(Bid.bid_no, Bid.created_at).all()

    # Build year list for selector
    years = [
        r[0]
        for r in db.session.query(Edition.year)
        .order_by(Edition.year.desc())
        .all()
    ]

    return render_template(
        "bids.html",
        bids=bids,
        year=year,
        years=years,
        search=search,
    )


@bp.route("/bids/export")
@login_required
def export_bids_csv():
    """Export bids for a year as CSV."""
    from flask import request, Response
    from app.extensions import db
    from app.models.bid import Bid
    from app.models.member import Member
    from app.models.item import Item
    from app.models.edition import Edition
    from sqlalchemy import func
    import csv
    import io

    year = request.args.get("year", type=int)
    if not year:
        latest = db.session.query(func.max(Edition.year)).scalar()
        year = latest or 2025

    bids = (
        Bid.query.options(
            db.joinedload(Bid.member),
            db.joinedload(Bid.item),
        )
        .filter(Bid.year == year)
        .order_by(Bid.bid_no, Bid.created_at)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "年份", "會員編號", "會員名稱", "聖物編號", "聖物名稱",
        "投標金額", "會員費", "已付金額", "付款方式", "經手人",
        "相片編號", "收據編號", "投標編號", "來源", "備註",
    ])

    for b in bids:
        writer.writerow([
            b.year,
            b.member.member_id if b.member else "",
            b.member.name if b.member else "",
            b.item.item_id if b.item else "",
            b.item.name_1_auspicious or b.item.name_2_description or "" if b.item else "",
            b.bid_amount or 0,
            b.membership_fee or 0,
            b.paid_amount or 0,
            b.payment_method or "",
            b.handler or "",
            b.photo_no or "",
            b.receipt_no or "",
            b.bid_no or "",
            b.source or "",
            b.remarks or "",
        ])

    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f'attachment; filename="bids_{year}.csv"',
        },
    )
