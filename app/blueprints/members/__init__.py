"""Members blueprint — 會員管理 CRUD."""
from flask import Blueprint

bp = Blueprint("members", __name__, template_folder="../templates/members")


@bp.route("/members")
def list_members():
    """List all members with optional search/filter."""
    from flask import render_template
    return render_template("members.html")


@bp.route("/members/<int:member_id>")
def member_detail(member_id):
    """Show member detail including bid history."""
    from flask import render_template
    return render_template("member_detail.html")
