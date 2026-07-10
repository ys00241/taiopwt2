"""Photos blueprint — 相片管理 / 圖庫."""
from flask import Blueprint

bp = Blueprint("photos", __name__, template_folder="../templates/photos",
               url_prefix="/photos")


@bp.route("/")
def photo_gallery():
    """Photo gallery main view."""
    from flask import render_template
    return render_template("photos.html")


@bp.route("/upload", methods=["POST"])
def photo_upload():
    """Upload one or more photos."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/<int:photo_id>")
def photo_detail(photo_id):
    """View a single photo."""
    from flask import jsonify
    return jsonify({"ok": True})


@bp.route("/<int:photo_id>/delete", methods=["POST"])
def photo_delete(photo_id):
    """Delete a photo."""
    from flask import jsonify
    return jsonify({"ok": True})
