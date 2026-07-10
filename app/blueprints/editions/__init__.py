"""Editions blueprint — 屆別管理."""
from flask import Blueprint

bp = Blueprint("editions", __name__, template_folder="../templates/editions")


@bp.route("/editions")
def list_editions():
    """List all editions (years) with summary data."""
    from flask import render_template
    return render_template("editions.html")


@bp.route("/editions/<int:edition_id>/edit", methods=["POST"])
def edit_edition(edition_id):
    """Update edition details."""
    from flask import jsonify
    return jsonify({"ok": True})
