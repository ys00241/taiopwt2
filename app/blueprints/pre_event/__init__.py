"""Pre-event blueprint — 前期準備 (上年欠款, 粉紅紙, 今年聖物, 支出, 贊助)."""
from flask import Blueprint

bp = Blueprint("pre_event", __name__, template_folder="../templates/pre_event",
               url_prefix="/pre")


@bp.route("/previous")
def previous_year():
    """上年資料 — Previous year debt overview."""
    from flask import render_template
    return render_template("pre_previous.html")


@bp.route("/previous/<int:member_id>")
def previous_member(member_id):
    """上年會員欠款詳情."""
    from flask import render_template
    return render_template("pre_previous_member.html")


@bp.route("/invoice/<int:member_id>")
def generate_invoice(member_id):
    """Generate 粉紅紙 (pink slip) DOCX."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/receipt/<int:member_id>")
def generate_receipt(member_id):
    """Generate PWT RECEIPT XLSX."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/items")
def pre_items():
    """今年聖物列表 — Current year items with sticker numbers."""
    from flask import render_template
    return render_template("pre_items.html")


@bp.route("/items/add", methods=["POST"])
def pre_items_add():
    """Add a new this-year item."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/items/import-csv", methods=["POST"])
def pre_items_import_csv():
    """Import items from CSV with auto sticker assignment."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/items/<int:item_id>/edit", methods=["POST"])
def pre_items_edit(item_id):
    """Edit a this-year item."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/items/<int:item_id>/delete", methods=["POST"])
def pre_items_delete(item_id):
    """Delete a this-year item."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/items/sticker-pdf")
def pre_items_sticker_pdf():
    """Generate sticker labels PDF."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/items/export-excel")
def pre_items_export_excel():
    """Export this-year items as XLSX."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/expenses")
def pre_expenses():
    """前期支出 — Pre-event expenses."""
    from flask import render_template
    return render_template("pre_expenses.html")


@bp.route("/expenses/add", methods=["POST"])
def pre_expenses_add():
    """Add a pre-event expense."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/expenses/<int:eid>/edit", methods=["POST"])
def pre_expenses_edit(eid):
    """Edit a pre-event expense."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/expenses/<int:eid>/delete", methods=["POST"])
def pre_expenses_delete(eid):
    """Delete a pre-event expense."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/sponsors")
def pre_sponsors():
    """贊助列表 — Sponsors."""
    from flask import render_template
    return render_template("pre_sponsors.html")


@bp.route("/sponsors/add", methods=["POST"])
def pre_sponsors_add():
    """Add a sponsor."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/sponsors/<int:sid>/edit", methods=["POST"])
def pre_sponsors_edit(sid):
    """Edit a sponsor."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/sponsors/<int:sid>/delete", methods=["POST"])
def pre_sponsors_delete(sid):
    """Delete a sponsor."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/expenses/categories")
def pre_expenses_categories():
    """Return predefined expense categories."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/expenses/import-categories", methods=["POST"])
def pre_expenses_import_categories():
    """Import expense categories from Excel."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/expenses/add-category", methods=["POST"])
def pre_expenses_add_category():
    """Add a new expense category."""
    from flask import jsonify
    return jsonify({"ok": True})
