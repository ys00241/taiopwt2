"""Manage blueprint — 系統管理 (login, settings, database)."""
from flask import Blueprint

bp = Blueprint("manage", __name__, template_folder="../templates/manage",
               url_prefix="/manage")


@bp.route("/login", methods=["GET", "POST"])
def login():
    """User login page."""
    from flask import render_template
    return render_template("login.html")


@bp.route("/logout")
def logout():
    """User logout."""
    from flask import redirect, url_for
    return redirect(url_for("dashboard.index"))


@bp.route("/settings")
def settings():
    """System settings."""
    from flask import render_template
    return render_template("settings.html")


@bp.route("/db-status")
def db_status():
    """Database status / admin panel."""
    from flask import jsonify
    return jsonify({"ok": True})
