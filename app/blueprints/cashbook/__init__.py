"""Cashbook blueprint — 現金收支日記帳 (Daily Cashbook).

Routes:
    GET  /            List entries with year/month filter + running balance
    POST /add         Create a new entry
    POST /<id>/edit   Update an entry
    POST /<id>/delete Delete an entry
    GET  /export      Download entries as CSV
    GET  /categories  Return income/expense category lists
"""
from datetime import date

from flask import Blueprint, Response, jsonify, request, render_template
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models.daily_entry import DailyEntry
from app.services.cashbook_service import (
    INCOME_CATEGORIES,
    EXPENSE_CATEGORIES,
    create_entry,
    delete_entry,
    export_csv,
    get_cashbook_summary,
    get_daily_entries,
    get_year,
    update_entry,
)

bp = Blueprint("cashbook", __name__, template_folder="../../templates/cashbook",
               url_prefix="/cashbook")


@bp.route("/")
@login_required
def cashbook_index():
    """Cashbook main view — daily entries listing with running balance.

    Query params:
        year (int): Filter year. Defaults to latest year with entries.
        month (int, optional): Filter month (1-12).

    Returns JSON with entries list and summary.
    """
    year = request.args.get("year", type=int) or get_year()
    month = request.args.get("month", type=int)

    entries = get_daily_entries(year, month)
    summary = get_cashbook_summary(year)

    return render_template("list.html",
                           year=year,
                           month=month,
                           entries=entries,
                           summary=summary,
                           income_categories=INCOME_CATEGORIES,
                           expense_categories=EXPENSE_CATEGORIES)


@bp.route("/add", methods=["POST"])
@login_required
def cashbook_add():
    """Add a daily entry.

    JSON body:
        entry_date (str, optional): ISO date. Defaults to today.
        entry_type (str): 'income' or 'expense'.
        category (str): Category from the predefined lists.
        subject (str): Required description.
        amount (float): Required amount.
        payment_method (str, optional): Payment method.
        handler (str, optional): Handler name. Defaults to current user.
        notes (str, optional): Additional notes.
    """
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"ok": False, "error": "請提供資料 (JSON body)"}), 400

    entry_type = data.get("entry_type", "").strip().lower()
    if entry_type not in ("income", "expense"):
        return jsonify({"ok": False, "error": "entry_type 必須為 income 或 expense"}), 400

    subject = (data.get("subject") or "").strip()
    if not subject:
        return jsonify({"ok": False, "error": "subject (項目) 不能為空"}), 400

    amount = data.get("amount")
    if amount is None:
        return jsonify({"ok": False, "error": "amount (金額) 不能為空"}), 400
    try:
        amount = float(amount)
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "amount 必須為數值"}), 400

    # Auto-fill handler from current user if auth is active
    from flask_login import current_user
    handler = data.get("handler", "")
    if not handler and current_user and current_user.is_authenticated:
        handler = getattr(current_user, "name", "") or getattr(current_user, "member_id", "")

    entry = create_entry({
        "year": data.get("year", date.today().year),
        "entry_date": data.get("entry_date"),
        "entry_type": entry_type,
        "category": data.get("category", ""),
        "subject": subject,
        "amount": amount,
        "payment_method": data.get("payment_method", ""),
        "handler": handler,
        "notes": data.get("notes", ""),
    })

    return jsonify({"ok": True, "entry": entry}), 201


@bp.route("/<int:eid>/edit", methods=["POST"])
@login_required
def cashbook_edit(eid):
    """Edit a daily entry.

    JSON body: Same fields as /add, all optional.
    """
    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"ok": False, "error": "請提供資料 (JSON body)"}), 400

    entry = update_entry(eid, data)
    if entry is None:
        return jsonify({"ok": False, "error": "記錄不存在"}), 404

    return jsonify({"ok": True, "entry": entry})


@bp.route("/<int:eid>/delete", methods=["POST"])
@login_required
def cashbook_delete(eid):
    """Delete a daily entry."""
    ok = delete_entry(eid)
    if not ok:
        return jsonify({"ok": False, "error": "記錄不存在"}), 404
    return jsonify({"ok": True})


@bp.route("/export")
@login_required
def cashbook_export():
    """Export cashbook entries as CSV download.

    Query params:
        year (int): Filter year. Defaults to latest.
        month (int, optional): Filter month.
    """
    year = request.args.get("year", type=int) or get_year()
    month = request.args.get("month", type=int)

    csv_content = export_csv(year, month)
    filename = f"cashbook_{year}"
    if month:
        filename += f"_{month:02d}"
    filename += ".csv"

    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8-sig",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@bp.route("/categories")
@login_required
def cashbook_categories():
    """Return income/expense category lists."""
    return jsonify({
        "ok": True,
        "income_categories": INCOME_CATEGORIES,
        "expense_categories": EXPENSE_CATEGORIES,
    })
