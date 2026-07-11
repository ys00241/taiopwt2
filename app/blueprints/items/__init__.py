"""Items blueprint — 聖物管理."""
import json

from flask import Blueprint, jsonify, render_template
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models.bid import Bid
from app.models.item import Item

bp = Blueprint("items", __name__)


@bp.route("/items")
@login_required
def list_items():
    """List all items with bid counts and yearly cost data."""
    items_raw = (
        db.session.query(
            Item,
            func.count(Bid.id).label("bid_count"),
            func.coalesce(
                func.sum(Bid.bid_amount).filter(Bid.bid_amount > 0),
                0,
            ).label("bid_total"),
        )
        .outerjoin(Bid, Bid.item_id == Item.item_id)
        .group_by(Item.id)
        .order_by(Item.item_id)
        .all()
    )

    result = []
    for item, bid_count, bid_total in items_raw:
        d = {
            "item_id": item.item_id,
            "name_1_auspicious": item.name_1_auspicious or "",
            "name_2_description": item.name_2_description or "",
            "year_data": item.year_data or "[]",
            "bid_count": bid_count,
            "bid_total": float(bid_total),
        }
        # Expand year_data JSON into separate rows
        year_data_list = json.loads(d["year_data"] or "[]")
        if year_data_list:
            for yd in year_data_list:
                row = dict(d)
                row["year"] = yd.get("year")
                row["cost_hkd"] = yd.get("cost_hkd")
                row["supplier"] = yd.get("supplier", "")
                result.append(row)
        else:
            d["year"] = None
            d["cost_hkd"] = None
            d["supplier"] = ""
            result.append(d)

    return render_template("items/items.html", items=result)


@bp.route("/items/<int:item_id>/detail")
@login_required
def item_detail(item_id):
    """Return item detail as JSON (API)."""
    item = Item.query.filter_by(item_id=item_id).first()
    if not item:
        return jsonify({"error": "Item not found"}), 404

    bid_count = Bid.query.filter_by(item_id=item_id).count()
    bid_total = (
        db.session.query(func.coalesce(func.sum(Bid.bid_amount), 0))
        .filter(Bid.item_id == item_id, Bid.bid_amount > 0)
        .scalar()
    )

    year_data = json.loads(item.year_data or "[]")

    return jsonify(
        {
            "item_id": item.item_id,
            "name_1_auspicious": item.name_1_auspicious or "",
            "name_2_description": item.name_2_description or "",
            "year_data": year_data,
            "bid_count": bid_count,
            "bid_total": float(bid_total),
            "created_at": (
                item.created_at.isoformat()
                if item.created_at
                else None
            ),
        }
    )


@bp.route("/items/<int:item_id>/edit", methods=["POST"])
@login_required
def item_edit(item_id):
    """Edit item's year_data (add/edit year entry)."""
    from flask import request
    from app.extensions import db

    item = Item.query.filter_by(item_id=item_id).first()
    if not item:
        return jsonify({"error": "Item not found"}), 404

    year = request.form.get("year", type=int)
    cost_hkd = request.form.get("cost_hkd", type=float)
    supplier = request.form.get("supplier", "").strip()

    if not year:
        return jsonify({"error": "年份為必填"}), 400

    year_data = json.loads(item.year_data or "[]")

    # Update existing or append new
    found = False
    for yd in year_data:
        if yd.get("year") == year:
            if cost_hkd is not None:
                yd["cost_hkd"] = cost_hkd
            if supplier:
                yd["supplier"] = supplier
            found = True
            break

    if not found:
        year_data.append({
            "year": year,
            "cost_hkd": cost_hkd,
            "supplier": supplier,
        })

    item.year_data = json.dumps(year_data)
    db.session.commit()

    return jsonify({"ok": True, "year_data": year_data})
