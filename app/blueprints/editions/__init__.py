"""Editions blueprint — 屆別管理."""
from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models.bid import Bid
from app.models.edition import Edition

bp = Blueprint("editions", __name__)


@bp.route("/editions")
@login_required
def list_editions():
    """List all editions (years) with summary bid data."""
    editions = (
        db.session.query(
            Edition,
            func.count(Bid.id).label("bid_count"),
            func.coalesce(
                func.sum(Bid.bid_amount).filter(Bid.bid_amount > 0),
                0,
            ).label("bid_total"),
            func.coalesce(
                func.sum(Bid.bid_amount - Bid.paid_amount).filter(
                    Bid.bid_amount > Bid.paid_amount
                ),
                0,
            ).label("unpaid_total"),
            func.count(func.nullif(Bid.membership_fee, 0)).label(
                "calc_member_count"
            ),
        )
        .outerjoin(Bid, Bid.year == Edition.year)
        .group_by(Edition.id)
        .order_by(Edition.year.desc())
        .all()
    )

    edition_list = []
    for ed, bid_count, bid_total, unpaid_total, calc_member_count in editions:
        edition_list.append(
            {
                "id": ed.id,
                "edition_id": ed.edition_id,
                "edition_no": ed.edition_no,
                "year": ed.year,
                "event_date": ed.event_date or "",
                "venue": ed.venue or "",
                "tables": ed.tables or 0,
                "singer": ed.singer or "",
                "member_count": ed.member_count or 0,
                "remarks": ed.remarks or "",
                "bid_count": bid_count,
                "bid_total": float(bid_total),
                "unpaid_total": float(unpaid_total),
                "calc_member_count": calc_member_count or 0,
            }
        )

    return render_template("editions/editions.html", editions=edition_list)


@bp.route("/editions/<int:edition_id>/edit", methods=["POST"])
@login_required
def edit_edition(edition_id):
    """Update edition details."""
    edition = Edition.query.get(edition_id)
    # The primary key is 'id' (String UUID), so we also try by edition_id
    if not edition:
        edition = Edition.query.filter_by(
            edition_id=edition_id
        ).first()
    if not edition:
        return jsonify({"error": "Edition not found"}), 404

    edition.event_date = request.form.get("event_date", "")
    edition.venue = request.form.get("venue", "")
    edition.tables = int(request.form.get("tables", 0) or 0)
    edition.singer = request.form.get("singer", "")
    edition.remarks = request.form.get("remarks", "")

    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/editions/<int:edition_id>/data")
@login_required
def edition_data(edition_id):
    """Return edition data as JSON (API)."""
    edition = Edition.query.get(edition_id)
    if not edition:
        edition = Edition.query.filter_by(
            edition_id=edition_id
        ).first()
    if not edition:
        return jsonify({"error": "Edition not found"}), 404

    # Compute bid stats
    bid_count = Bid.query.filter_by(year=edition.year).count()
    bid_total = (
        db.session.query(func.coalesce(func.sum(Bid.bid_amount), 0))
        .filter(Bid.year == edition.year, Bid.bid_amount > 0)
        .scalar()
    )
    unpaid_total = (
        db.session.query(
            func.coalesce(
                func.sum(Bid.bid_amount - Bid.paid_amount), 0
            )
        )
        .filter(
            Bid.year == edition.year, Bid.bid_amount > Bid.paid_amount
        )
        .scalar()
    )

    return jsonify(
        {
            "id": edition.id,
            "edition_id": edition.edition_id,
            "edition_no": edition.edition_no,
            "year": edition.year,
            "event_date": edition.event_date or "",
            "venue": edition.venue or "",
            "tables": edition.tables or 0,
            "singer": edition.singer or "",
            "member_count": edition.member_count or 0,
            "remarks": edition.remarks or "",
            "bid_count": bid_count,
            "bid_total": float(bid_total),
            "unpaid_total": float(unpaid_total),
        }
    )
