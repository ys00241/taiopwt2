"""Live-event blueprint — 現場活動 (收款, 現場支出), mobile-optimized."""
from flask import Blueprint

bp = Blueprint("live_event", __name__, template_folder="../templates/live_event",
               url_prefix="/live")


@bp.route("/payments")
def live_payments():
    """現場收款 — Live payment collection."""
    from flask import render_template
    return render_template("live_payments.html")


@bp.route("/payments/add", methods=["POST"])
def live_payments_add():
    """Record a live payment."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/payments/<int:pid>/edit", methods=["POST"])
def live_payments_edit(pid):
    """Edit a live payment."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/expenses")
def live_expenses():
    """現場支出 — Live event expenses."""
    from flask import render_template
    return render_template("live_expenses.html")


@bp.route("/expenses/add", methods=["POST"])
def live_expenses_add():
    """Add a live expense."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/expenses/<int:eid>/delete", methods=["POST"])
def live_expenses_delete(eid):
    """Delete a live expense."""
    from flask import jsonify
    return jsonify({"ok": True})
