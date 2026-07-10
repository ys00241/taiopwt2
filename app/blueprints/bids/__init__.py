"""Bids blueprint — 投標記錄."""
from flask import Blueprint

bp = Blueprint("bids", __name__, template_folder="../templates/bids")


@bp.route("/bids")
def list_bids():
    """List bids with optional year/search filters."""
    from flask import render_template
    return render_template("bids.html")
