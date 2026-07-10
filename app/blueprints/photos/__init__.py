"""Photos blueprint — 相片管理 / 圖庫.

Routes:
    GET   /                                    Gallery grid view (year filter)
    POST  /upload                              Upload photo file(s)
    GET   /<id>                                Photo detail + linked items
    POST  /<id>/delete                         Delete photo
    POST  /<id>/link                           Link photo to target
    POST  /<id>/unlink/<link_id>               Remove link
    GET   /<id>/thumbnail                      Serve thumbnail image
    GET   /by-target/<table>/<id>              Photos linked to a record
"""
from datetime import date
from pathlib import Path

from flask import Blueprint, Response, jsonify, request, send_file, render_template
from flask_login import login_required
from sqlalchemy import func

from app.extensions import db
from app.models.photo import Photo
from app.services.photo_service import (
    delete_photo,
    get_photo,
    get_photos,
    get_photos_for_entity,
    link_photo,
    process_upload,
    unlink_photo,
)
from flask import current_app

bp = Blueprint("photos", __name__, template_folder="../templates/photos",
               url_prefix="/photos")


def _get_default_year() -> int:
    """Get the default year (latest year with photos, or current year)."""
    max_year = db.session.query(func.max(Photo.year)).scalar()
    return max_year or date.today().year


@bp.route("/")
@login_required
def photo_gallery():
    """Photo gallery grid view.

    Query params:
        year (int): Filter year. Defaults to latest year.

    Returns JSON list of photos.
    """
    year = request.args.get("year", type=int) or _get_default_year()
    photos = get_photos(year)
    return render_template("gallery.html",
                           year=year,
                           photos=photos)


@bp.route("/upload", methods=["POST"])
@login_required
def photo_upload():
    """Upload one or more photos.

    Accepts multipart/form-data with one or more files under the 'files' key.

    Form fields:
        files: One or more file attachments.
        year (int, optional): Association year. Defaults to current year.
        target_table (str, optional): Auto-link to this table.
        target_id (int, optional): Auto-link to this record ID.

    Returns JSON with uploaded photo info.
    """
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"ok": False, "error": "未選擇檔案"}), 400

    year = request.form.get("year", type=int) or date.today().year
    target_table = request.form.get("target_table")
    target_id = request.form.get("target_id", type=int)

    # Try to get uploader from auth
    from flask_login import current_user
    uploaded_by = ""
    if current_user and current_user.is_authenticated:
        uploaded_by = getattr(current_user, "name", "") or getattr(current_user, "member_id", "")

    results = []
    errors = []

    for f in files:
        if f.filename == "":
            continue
        result = process_upload(
            f,
            year=year,
            uploaded_by=uploaded_by,
            target_table=target_table,
            target_id=target_id,
        )
        if result.get("ok"):
            results.append(result)
        else:
            errors.append({"filename": f.filename, "error": result.get("error", "處理失敗")})

    return jsonify({
        "ok": len(results) > 0,
        "uploaded": results,
        "errors": errors,
        "total": len(results),
    }), 201 if results else 400


@bp.route("/<int:photo_id>")
@login_required
def photo_detail(photo_id):
    """View a single photo with its linked items."""
    photo = get_photo(photo_id)
    if not photo:
        return jsonify({"ok": False, "error": "相片不存在"}), 404
    return jsonify({"ok": True, "photo": photo})


@bp.route("/<int:photo_id>/delete", methods=["POST"])
@login_required
def photo_delete(photo_id):
    """Delete a photo (file + DB record)."""
    ok = delete_photo(photo_id)
    if not ok:
        return jsonify({"ok": False, "error": "相片不存在"}), 404
    return jsonify({"ok": True})


@bp.route("/<int:photo_id>/link", methods=["POST"])
@login_required
def photo_link(photo_id):
    """Link a photo to a target entity.

    JSON body:
        target_table (str): Required. Table name (e.g. 'item', 'member').
        target_id (int): Required. Record ID.
        caption (str, optional): Caption for the link.
        sort_order (int, optional): Sort order.
    """
    data = request.get_json(silent=True) or {}
    target_table = data.get("target_table", "").strip()
    target_id = data.get("target_id")

    if not target_table:
        return jsonify({"ok": False, "error": "target_table 不能為空"}), 400
    if target_id is None:
        return jsonify({"ok": False, "error": "target_id 不能為空"}), 400

    try:
        target_id = int(target_id)
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "target_id 必須為整數"}), 400

    result = link_photo(
        photo_id=photo_id,
        target_table=target_table,
        target_id=target_id,
        caption=data.get("caption", ""),
        sort_order=int(data.get("sort_order", 0)),
    )
    if result is None:
        return jsonify({"ok": False, "error": "相片不存在"}), 404

    return jsonify({"ok": True, "link": result}), 201


@bp.route("/<int:photo_id>/unlink/<int:link_id>", methods=["POST"])
@login_required
def photo_unlink(photo_id, link_id):
    """Remove a specific link from a photo."""
    ok = unlink_photo(link_id)
    if not ok:
        return jsonify({"ok": False, "error": "關聯不存在"}), 404
    return jsonify({"ok": True})


@bp.route("/<int:photo_id>/thumbnail")
@login_required
def photo_thumbnail(photo_id):
    """Serve the thumbnail image for a photo.

    Returns the actual image file (or placeholder if not found).
    """
    from app.services.photo_service import _get_upload_base, _create_placeholder_thumbnail
    import tempfile

    photo = Photo.query.get(photo_id)
    if not photo:
        # Return placeholder for missing photo
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        _create_placeholder_thumbnail(tmp.name)
        return send_file(tmp.name, mimetype="image/jpeg")

    upload_base = _get_upload_base()
    thumb_path = upload_base / (photo.thumbnail_path or "")

    if not thumb_path.exists():
        # Fallback: try the original image
        orig_path = upload_base / photo.stored_path
        if orig_path.exists():
            return send_file(str(orig_path), mimetype=photo.mime_type or "image/jpeg")
        # Placeholder
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        _create_placeholder_thumbnail(tmp.name)
        return send_file(tmp.name, mimetype="image/jpeg")

    return send_file(str(thumb_path), mimetype=photo.mime_type or "image/jpeg")


@bp.route("/by-target/<target_table>/<int:target_id>")
@login_required
def photos_by_target(target_table, target_id):
    """Get all photos linked to a specific record.

    Args:
        target_table: Table name (e.g. 'item', 'member', 'this_year_item').
        target_id: Record ID.
    """
    photos = get_photos_for_entity(target_table, target_id)
    return jsonify({
        "ok": True,
        "target_table": target_table,
        "target_id": target_id,
        "photos": photos,
    })
