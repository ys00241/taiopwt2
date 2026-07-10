"""Cashbook blueprint — 現金收支日記帳 (Daily Cashbook)."""
from flask import Blueprint

bp = Blueprint("cashbook", __name__, template_folder="../templates/cashbook",
               url_prefix="/cashbook")


@bp.route("/")
def cashbook_index():
    """Cashbook main view — daily entries listing."""
    from flask import render_template
    return render_template("cashbook.html")


@bp.route("/add", methods=["POST"])
def cashbook_add():
    """Add a daily entry."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/<int:eid>/edit", methods=["POST"])
def cashbook_edit(eid):
    """Edit a daily entry."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/<int:eid>/delete", methods=["POST"])
def cashbook_delete(eid):
    """Delete a daily entry."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/export")
def cashbook_export():
    """Export cashbook as XLSX."""
    from flask import jsonify
    return jsonify({"ok": True})
