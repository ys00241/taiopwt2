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
from app.models.membership_fee import MembershipFee

bp = Blueprint("members", __name__)


@bp.route("/members")
@login_required
def list_members():
    """List all members with optional search/filter."""
    search = request.args.get("q", "").strip()
    unpaid_filter = request.args.get("unpaid", "").strip()
    year = request.args.get("year", type=int) or 0

    all_years = [
        r[0]
        for r in db.session.query(func.distinct(Bid.year))
        .order_by(Bid.year.desc())
        .all()
    ]

    # Get all members with computed totals via subqueries
    due_query = (
        db.session.query(
            Bid.member_id,
            func.coalesce(func.sum(Bid.bid_amount), 0).label("total_due"),
        )
        .filter(Bid.bid_amount > 0)
    )
    if year > 0:
        due_query = due_query.filter(Bid.year == year)
    due_sub = due_query.group_by(Bid.member_id).subquery()

    paid_query = (
        db.session.query(
            Bid.member_id,
            func.coalesce(func.sum(Bid.paid_amount), 0).label("total_paid"),
        )
    )
    if year > 0:
        paid_query = paid_query.filter(Bid.year == year)
    paid_sub = paid_query.group_by(Bid.member_id).subquery()

    last_pay_sub = (
        db.session.query(
            LiveIncome.member_id,
            func.max(LiveIncome.created_at).label("last_pay_date"),
        )
        .group_by(LiveIncome.member_id)
        .subquery()
    )

    # Filters
    member_type_filter = request.args.get("member_type", "").strip()
    status_filter = request.args.get("status", "").strip()

    query = (
        db.session.query(
            Member.member_id,
            Member.name,
            Member.phone,
            Member.phone_2,
            Member.home_address,
            Member.first_year,
            Member.member_type,
            Member.status,
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
                "member_type": r.member_type or "member",
                "status": r.status or "active",
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

    # Member type filter
    if member_type_filter in ("member", "friend"):
        members_list = [
            m for m in members_list if m["member_type"] == member_type_filter
        ]

    # Status filter
    if status_filter in ("active", "inactive"):
        members_list = [
            m for m in members_list if m["status"] == status_filter
        ]

    return render_template(
        "members/members.html",
        members=members_list,
        search=search,
        member_type=member_type_filter,
        status=status_filter,
        selected_year=year,
        all_years=all_years,
    )


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
                "item_id": b.item_id,
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
        "members/member_detail.html",
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
    member_type = request.form.get("member_type", "member").strip()
    status = request.form.get("status", "active").strip()

    if not name:
        return jsonify({"error": "會員姓名為必填"}), 400

    # Auto-assign random 3-digit member_id (100-999)
    import random
    used_ids = {r[0] for r in db.session.query(Member.member_id).all()}
    available = [i for i in range(100, 1000) if i not in used_ids]
    new_member_id = random.choice(available) if available else 999
    import uuid

    member = Member(
        id=str(uuid.uuid4()),
        member_id=new_member_id,
        name=name,
        phone=phone or None,
        phone_2=phone_2 or None,
        home_address=home_address or None,
        first_year=int(first_year_str) if first_year_str else None,
        member_type=member_type if member_type in ("member", "friend") else "member",
        status=status if status in ("active", "inactive") else "active",
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
    member_type = request.form.get("member_type", "").strip()
    if member_type in ("member", "friend"):
        member.member_type = member_type
    status = request.form.get("status", "").strip()
    if status in ("active", "inactive"):
        member.status = status

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
            "member_type",
            "status",
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
                m.member_type or "member",
                m.status or "active",
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
            member_type=(
                row.get("member_type", "member").strip()
                if row.get("member_type", "").strip() in ("member", "friend")
                else "member"
            ),
            status=(
                row.get("status", "active").strip()
                if row.get("status", "").strip() in ("active", "inactive")
                else "active"
            ),
        )
        db.session.add(member)
        next_id += 1
        count += 1

    db.session.commit()
    return jsonify(
        {"ok": True, "count": count, "errors": errors}
    )


# ════════════════════════════════════════════════════════════════════════
#  Membership Fee CRUD (會費管理)
# ════════════════════════════════════════════════════════════════════════

@bp.route("/members/<int:member_id>/fees")
@login_required
def member_fees_list(member_id):
    """List membership fees for a member."""
    fees = (
        MembershipFee.query
        .filter_by(member_id=member_id)
        .order_by(MembershipFee.year.desc())
        .all()
    )
    return jsonify({
        "fees": [
            {
                "id": f.id,
                "year": f.year,
                "amount": f.amount or 0,
                "payment_method": f.payment_method or "",
                "handler": f.handler or "",
                "notes": f.notes or "",
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in fees
        ]
    })


@bp.route("/members/<int:member_id>/fees/add", methods=["POST"])
@login_required
def member_fees_add(member_id):
    """Add a membership fee record."""
    member = Member.query.filter_by(member_id=member_id).first()
    if not member:
        return jsonify({"error": "會員不存在"}), 404

    year = int(request.form.get("year", 0))
    amount = float(request.form.get("amount", 0) or 0)
    payment_method = request.form.get("payment_method", "").strip()
    handler = request.form.get("handler", "").strip()
    notes = request.form.get("notes", "").strip()

    fee = MembershipFee(
        member_id=member_id,
        year=year,
        amount=amount,
        payment_method=payment_method,
        handler=handler,
        notes=notes,
    )
    db.session.add(fee)
    db.session.commit()
    return jsonify({"ok": True, "fee_id": fee.id})


@bp.route("/members/<int:member_id>/fees/<fee_id>/edit", methods=["POST"])
@login_required
def member_fees_edit(member_id, fee_id):
    """Edit a membership fee record."""
    fee = db.session.get(MembershipFee, fee_id)
    if not fee or fee.member_id != member_id:
        return jsonify({"error": "會費記錄不存在"}), 404

    year = request.form.get("year")
    if year:
        fee.year = int(year)
    amount = request.form.get("amount")
    if amount:
        fee.amount = float(amount)
    payment_method = request.form.get("payment_method")
    if payment_method is not None:
        fee.payment_method = payment_method.strip()
    handler = request.form.get("handler")
    if handler is not None:
        fee.handler = handler.strip()
    notes = request.form.get("notes")
    if notes is not None:
        fee.notes = notes.strip()

    db.session.commit()
    return jsonify({"ok": True})


@bp.route("/members/<int:member_id>/fees/<fee_id>/delete", methods=["POST"])
@login_required
def member_fees_delete(member_id, fee_id):
    """Delete a membership fee record (admin only)."""
    from flask_login import current_user
    if current_user.role != "admin":
        return jsonify({"error": "僅管理員可執行此操作"}), 403

    fee = db.session.get(MembershipFee, fee_id)
    if not fee or fee.member_id != member_id:
        return jsonify({"error": "會費記錄不存在"}), 404

    db.session.delete(fee)
    db.session.commit()
    return jsonify({"ok": True})
