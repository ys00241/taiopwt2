"""Members blueprint — 會員管理 CRUD."""
import csv
import io

from flask import Blueprint, jsonify, render_template, request, send_file
from flask_login import login_required
from sqlalchemy import func, or_

from app.extensions import db
from app.models.bid import Bid
from app.models.item import Item
from app.models.live_income import LiveIncome
from app.models.member import Member

bp = Blueprint("members", __name__)


@bp.route("/members")
@login_required
def list_members():
    """List all members with optional search/filter."""
    search = request.args.get("q", "").strip()
    unpaid_filter = request.args.get("unpaid", "").strip()

    # Get all members with computed totals via subqueries
    due_sub = (
        db.session.query(
            Bid.member_id,
            func.coalesce(func.sum(Bid.bid_amount), 0).label("total_due"),
        )
        .filter(Bid.bid_amount > 0)
        .group_by(Bid.member_id)
        .subquery()
    )

    paid_sub = (
        db.session.query(
            Bid.member_id,
            func.coalesce(func.sum(Bid.paid_amount), 0).label("total_paid"),
        )
        .group_by(Bid.member_id)
        .subquery()
    )

    last_pay_sub = (
        db.session.query(
            LiveIncome.member_id,
            func.max(LiveIncome.created_at).label("last_pay_date"),
        )
        .group_by(LiveIncome.member_id)
        .subquery()
    )

    query = (
        db.session.query(
            Member.member_id,
            Member.name,
            Member.phone,
            Member.phone_2,
            Member.home_address,
            Member.first_year,
            func.coalesce(due_sub.c.total_due, 0).label("total_due"),
            func.coalesce(paid_sub.c.total_paid, 0).label("total_paid"),
            last_pay_sub.c.last_pay_date,
        )
        .outerjoin(due_sub, Member.member_id == due_sub.c.member_id)
        .outerjoin(paid_sub, Member.member_id == paid_sub.c.member_id)
        .outerjoin(
            last_pay_sub, Member.member_id == last_pay_sub.c.member_id
        )
        .order_by(Member.member_id)
    )

    results = query.all()

    # Build result list as dicts
    members_list = []
    for r in results:
        members_list.append(
            {
                "member_id": r.member_id,
                "name": r.name,
                "phone": r.phone or "",
                "phone_2": r.phone_2 or "",
                "home_address": r.home_address or "",
                "first_year": r.first_year,
                "total_due": float(r.total_due),
                "total_paid": float(r.total_paid),
                "last_pay_date": r.last_pay_date,
            }
        )

    # Search: by name or phone
    if search:
        # Name/phone match
        direct_match_ids = {
            m["member_id"]
            for m in members_list
            if search.lower() in (m["name"] or "").lower()
            or search.lower() in (m["phone"] or "").lower()
            or search.lower() in (m["phone_2"] or "").lower()
        }
        # Also search by item names in bids
        item_member_rows = (
            db.session.query(Bid.member_id)
            .join(Item, Bid.item_id == Item.item_id)
            .filter(
                or_(
                    Item.name_1_auspicious.ilike(f"%{search}%"),
                    Item.name_2_description.ilike(f"%{search}%"),
                )
            )
            .distinct()
            .all()
        )
        item_match_ids = {r.member_id for r in item_member_rows}
        members_list = [
            m
            for m in members_list
            if m["member_id"] in direct_match_ids
            or m["member_id"] in item_match_ids
        ]

    # Unpaid filter
    if unpaid_filter == "yes":
        members_list = [
            m
            for m in members_list
            if (m["total_due"] - m["total_paid"]) > 0
        ]
    elif unpaid_filter == "no":
        members_list = [
            m
            for m in members_list
            if (m["total_due"] - m["total_paid"]) <= 0
        ]

    return render_template("members/members.html", members=members_list, search=search)


@bp.route("/members/<int:member_id>")
@login_required
def member_detail(member_id):
    """Show member detail including bid history."""
    member = Member.query.filter_by(member_id=member_id).first()
    if not member:
        return render_template("errors/404.html"), 404

    # Get bid history with item info, grouped by year
    bids = (
        db.session.query(Bid, Item.name_1_auspicious, Item.name_2_description)
        .outerjoin(Item, Bid.item_id == Item.item_id)
        .filter(Bid.member_id == member_id)
        .order_by(Bid.year.desc(), Bid.bid_no)
        .all()
    )

    total_due = (
        db.session.query(func.coalesce(func.sum(Bid.bid_amount), 0))
        .filter(Bid.member_id == member_id, Bid.bid_amount > 0)
        .scalar()
    )
    total_paid = (
        db.session.query(func.coalesce(func.sum(Bid.paid_amount), 0))
        .filter(Bid.member_id == member_id)
        .scalar()
    )

    bid_list = []
    for b, name1, name2 in bids:
        bid_list.append(
            {
                "id": b.id,
                "year": b.year,
                "bid_amount": b.bid_amount or 0,
                "paid_amount": b.paid_amount or 0,
                "membership_fee": b.membership_fee or 0,
                "bid_no": b.bid_no,
                "payment_method": b.payment_method or "",
                "handler": b.handler or "",
                "receipt_no": b.receipt_no or "",
                "remarks": b.remarks or "",
                "item_name": name1 or name2 or "",
                "name_1_auspicious": name1 or "",
                "name_2_description": name2 or "",
            }
        )

    return render_template(
        "member_detail.html",
        member=member,
        bids=bid_list,
        total=[float(total_due), float(total_paid)],
    )


@bp.route("/members/add", methods=["POST"])
@login_required
def add_member():
    """Add a new member."""
    name = request.form.get("name", "").strip()
    phone = request.form.get("phone", "").strip()
    phone_2 = request.form.get("phone_2", "").strip()
    home_address = request.form.get("home_address", "").strip()
    first_year_str = request.form.get("first_year", "").strip()

    if not name:
        return jsonify({"error": "會員姓名為必填"}), 400

    # Auto-assign member_id
    max_id = (
        db.session.query(func.max(Member.member_id)).scalar() or 0
    )
    new_member_id = max_id + 1
    import uuid

    member = Member(
        id=str(uuid.uuid4()),
        member_id=new_member_id,
        name=name,
        phone=phone or None,
        phone_2=phone_2 or None,
        home_address=home_address or None,
        first_year=int(first_year_str) if first_year_str else None,
    )
    db.session.add(member)
    db.session.commit()

    return jsonify(
        {"ok": True, "member_id": new_member_id, "name": name}
    )


@bp.route("/members/<int:member_id>/edit", methods=["POST"])
@login_required
def edit_member(member_id):
    """Edit an existing member."""
    member = Member.query.filter_by(member_id=member_id).first()
    if not member:
        return jsonify({"error": "會員不存在"}), 404

    name = request.form.get("name", "").strip()
    if not name:
        return jsonify({"error": "會員姓名為必填"}), 400

    member.name = name
    member.phone = request.form.get("phone", "").strip() or None
    member.phone_2 = (
        request.form.get("phone_2", "").strip() or None
    )
    member.home_address = (
        request.form.get("home_address", "").strip() or None
    )
    first_year_str = request.form.get("first_year", "").strip()
    member.first_year = (
        int(first_year_str) if first_year_str else None
    )

    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/members/<int:member_id>/delete", methods=["POST"])
@login_required
def delete_member(member_id):
    """Delete a member."""
    from flask_login import current_user
    if current_user.role != "admin":
        return jsonify({"error": "僅管理員可執行刪除操作"}), 403
    member = Member.query.filter_by(member_id=member_id).first()
    if not member:
        return jsonify({"error": "會員不存在"}), 404

    db.session.delete(member)
    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/members/export")
@login_required
def export_members():
    """Export all members as CSV."""
    members = Member.query.order_by(Member.member_id).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "member_id",
            "name",
            "phone",
            "phone_2",
            "home_address",
            "first_year",
        ]
    )
    for m in members:
        writer.writerow(
            [
                m.member_id,
                m.name,
                m.phone or "",
                m.phone_2 or "",
                m.home_address or "",
                m.first_year or "",
            ]
        )

    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode("utf-8-sig")),
        mimetype="text/csv; charset=utf-8",
        as_attachment=True,
        download_name="members_export.csv",
    )


@bp.route("/members/import", methods=["POST"])
@login_required
def import_members():
    """Import members from CSV (name required)."""
    from flask_login import current_user
    if current_user.role != "admin":
        return jsonify({"error": "僅管理員可執行匯入操作"}), 403
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "請上載檔案"}), 400

    content = f.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(content))

    max_id = (
        db.session.query(func.max(Member.member_id)).scalar() or 0
    )
    next_id = max_id + 1
    count = 0
    errors = []
    import uuid

    for row_idx, row in enumerate(reader, start=2):
        name = (row.get("name") or "").strip()
        if not name:
            errors.append(f"第{row_idx}行: 姓名為必填")
            continue

        member = Member(
            id=str(uuid.uuid4()),
            member_id=next_id,
            name=name,
            phone=(row.get("phone") or "").strip() or None,
            phone_2=(row.get("phone_2") or "").strip() or None,
            home_address=(
                (row.get("home_address") or "").strip() or None
            ),
            first_year=(
                int(row.get("first_year", "").strip())
                if row.get("first_year", "").strip()
                else None
            ),
        )
        db.session.add(member)
        next_id += 1
        count += 1

    db.session.commit()
    return jsonify(
        {"ok": True, "count": count, "errors": errors}
    )
