"""PL blueprint — 損益表 (Profit & Loss)."""
from flask import Blueprint

bp = Blueprint("pl", __name__, template_folder="../templates/pl")


@bp.route("/pl")
def view_pl():
    """View profit & loss entries by year."""
    from flask import render_template
    return render_template("pl.html")
