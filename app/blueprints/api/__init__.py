"""API blueprint — RESTful JSON endpoints for AJAX and external integration."""
from flask import Blueprint

bp = Blueprint("api", __name__, template_folder="../templates/api")


@bp.route("/categories")
def api_categories():
    """Return expense categories as JSON."""
    from flask import jsonify
    return jsonify({"ok": True, "categories": []})


@bp.route("/stats")
def api_stats():
    """Return dashboard statistics as JSON."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/search")
def api_search():
    """Universal search endpoint."""
    from flask import jsonify
    return jsonify({"ok": True, "results": []})
