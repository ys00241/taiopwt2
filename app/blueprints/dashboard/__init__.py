"""Dashboard blueprint — main overview & statistics."""
from flask import Blueprint

bp = Blueprint("dashboard", __name__, template_folder="../templates/dashboard")


@bp.route("/")
def index():
    """Main dashboard — overview statistics for the current year."""
    from flask import render_template
    from app.extensions import db
    return render_template("dashboard.html")
