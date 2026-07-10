"""Items blueprint — 聖物管理."""
from flask import Blueprint

bp = Blueprint("items", __name__, template_folder="../templates/items")


@bp.route("/items")
def list_items():
    """List all items with bid counts and yearly cost data."""
    from flask import render_template
    return render_template("items.html")
