"""Photo service — photo upload, linking, thumbnail generation, and gallery logic."""
import os
import uuid
from datetime import date
from pathlib import Path

from flask import current_app
from werkzeug.utils import secure_filename
from PIL import Image

from app.extensions import db
from app.models.photo import Photo
from app.models.photo_link import PhotoLink


THUMB_WIDTH = 300
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
UPLOAD_SUBDIR = "items"   # files go under uploads/items/{year}/


def _allowed_file(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def _get_upload_base() -> Path:
    """Get the base upload directory from config."""
    return Path(current_app.config.get("UPLOADS_DIR", "uploads"))


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def process_upload(file_storage, year: int, uploaded_by: str = "",
                   target_table: str | None = None,
                   target_id: int | None = None) -> dict:
    """Process an uploaded photo file.

    Steps:
      1. Validate file type.
      2. Generate a unique stored filename.
      3. Save original to uploads/items/{year}/{stored_filename}.
      4. Generate 300px-wide thumbnail.
      5. Create Photo DB record.
      6. Optionally create PhotoLink record.

    Args:
        file_storage: Flask FileStorage object.
        year: Association year.
        uploaded_by: Uploader name (default empty).
        target_table: Optional target table for linking.
        target_id: Optional target ID for linking.

    Returns:
        Dict with photo record info.
    """
    if not file_storage or not file_storage.filename:
        return {"ok": False, "error": "未選擇檔案"}

    original_name = secure_filename(file_storage.filename or "upload")
    if not original_name:
        original_name = f"upload_{uuid.uuid4().hex[:8]}"

    ext = Path(original_name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return {"ok": False, "error": f"不支援的檔案格式: {ext}"}

    # Unique stored filename
    stored_name = f"{uuid.uuid4().hex}{ext}"
    year_str = str(year)

    # Directory: uploads/items/{year}/
    upload_dir = _ensure_dir(_get_upload_base() / UPLOAD_SUBDIR / year_str)
    stored_path = upload_dir / stored_name

    # Save original file
    file_storage.save(str(stored_path))
    file_size = stored_path.stat().st_size

    # Generate thumbnail
    thumb_dir = _ensure_dir(upload_dir / "thumbnails")
    thumb_name = f"thumb_{stored_name}"
    thumb_path = thumb_dir / thumb_name
    mime_type = _generate_thumbnail(str(stored_path), str(thumb_path))

    # Relative paths for DB storage (relative to uploads base)
    rel_stored = str(Path(UPLOAD_SUBDIR) / year_str / stored_name)
    rel_thumb = str(Path(UPLOAD_SUBDIR) / year_str / "thumbnails" / thumb_name)

    # Create Photo record
    photo = Photo(
        year=year,
        filename=original_name,
        stored_path=rel_stored,
        thumbnail_path=rel_thumb,
        mime_type=mime_type or "image/jpeg",
        file_size=file_size,
        uploaded_by=uploaded_by,
    )
    db.session.add(photo)
    db.session.flush()  # get photo.id

    # Optionally link to target
    if target_table and target_id is not None:
        link = PhotoLink(
            photo_id=photo.id,
            target_table=target_table,
            target_id=int(target_id),
        )
        db.session.add(link)

    db.session.commit()

    return {
        "ok": True,
        "id": photo.id,
        "filename": photo.filename,
        "stored_path": photo.stored_path,
        "thumbnail_path": photo.thumbnail_path,
        "file_size": photo.file_size,
        "mime_type": photo.mime_type,
        "year": photo.year,
        "uploaded_at": photo.uploaded_at.isoformat() if photo.uploaded_at else "",
    }


def _generate_thumbnail(source_path: str, thumb_path: str, width: int = THUMB_WIDTH) -> str:
    """Generate a thumbnail for the given image.

    Args:
        source_path: Path to original image.
        thumb_path: Path to save thumbnail.
        width: Target width in pixels.

    Returns:
        MIME type string.
    """
    try:
        img = Image.open(source_path)
        mime = img.format or "JPEG"
        mime_type = Image.MIME.get(mime, "image/jpeg")

        # Calculate proportional height
        w_percent = width / float(img.size[0])
        height = int(float(img.size[1]) * float(w_percent))
        img = img.resize((width, height), Image.LANCZOS)

        # Convert RGBA/P to RGB for JPEG save
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        img.save(thumb_path, "JPEG", quality=85)
        return mime_type
    except Exception:
        # If thumbnail generation fails, save a placeholder
        _create_placeholder_thumbnail(thumb_path)
        return "image/jpeg"


def _create_placeholder_thumbnail(path: str, width: int = THUMB_WIDTH, height: int = THUMB_WIDTH):
    """Create a simple placeholder thumbnail if image processing fails."""
    img = Image.new("RGB", (width, height), (200, 200, 200))
    img.save(path, "JPEG", quality=50)


def get_photo(photo_id: int) -> dict | None:
    """Get a single photo record with its links.

    Args:
        photo_id: Photo ID.

    Returns:
        Photo dict with links, or None.
    """
    photo = Photo.query.get(photo_id)
    if not photo:
        return None

    links = PhotoLink.query.filter_by(photo_id=photo_id).order_by(PhotoLink.sort_order).all()

    return {
        "id": photo.id,
        "year": photo.year,
        "filename": photo.filename,
        "stored_path": photo.stored_path,
        "thumbnail_path": photo.thumbnail_path,
        "mime_type": photo.mime_type,
        "file_size": photo.file_size,
        "uploaded_by": photo.uploaded_by or "",
        "uploaded_at": photo.uploaded_at.isoformat() if photo.uploaded_at else "",
        "created_at": photo.created_at.isoformat() if photo.created_at else "",
        "links": [
            {
                "id": link.id,
                "photo_id": link.photo_id,
                "target_table": link.target_table,
                "target_id": link.target_id,
                "sort_order": link.sort_order,
                "caption": link.caption or "",
            }
            for link in links
        ],
    }


def delete_photo(photo_id: int) -> bool:
    """Delete a photo and its files.

    Args:
        photo_id: Photo ID.

    Returns:
        True if deleted, False if not found.
    """
    photo = Photo.query.get(photo_id)
    if not photo:
        return False

    # Delete physical files
    upload_base = _get_upload_base()
    stored_file = upload_base / photo.stored_path
    if stored_file.exists():
        stored_file.unlink()

    if photo.thumbnail_path:
        thumb_file = upload_base / photo.thumbnail_path
        if thumb_file.exists():
            thumb_file.unlink()

    # Delete DB record (cascades to PhotoLink)
    db.session.delete(photo)
    db.session.commit()
    return True


def get_photos(year: int | None = None) -> list[dict]:
    """Get list of photos, optionally filtered by year.

    Args:
        year: Optional year filter.

    Returns:
        List of photo dicts.
    """
    q = Photo.query
    if year is not None:
        q = q.filter(Photo.year == year)
    photos = q.order_by(Photo.created_at.desc()).all()

    return [
        {
            "id": p.id,
            "year": p.year,
            "filename": p.filename,
            "stored_path": p.stored_path,
            "thumbnail_path": p.thumbnail_path,
            "mime_type": p.mime_type,
            "file_size": p.file_size,
            "uploaded_by": p.uploaded_by or "",
            "uploaded_at": p.uploaded_at.isoformat() if p.uploaded_at else "",
            "created_at": p.created_at.isoformat() if p.created_at else "",
        }
        for p in photos
    ]


def get_photos_for_entity(target_table: str, target_id: int) -> list[dict]:
    """Get all photos linked to a given entity.

    Args:
        target_table: e.g. 'item', 'member', 'this_year_item'.
        target_id: The entity's ID.

    Returns:
        List of Photo dicts.
    """
    links = (
        PhotoLink.query
        .filter_by(target_table=target_table, target_id=target_id)
        .order_by(PhotoLink.sort_order)
        .all()
    )

    results = []
    for link in links:
        photo = Photo.query.get(link.photo_id)
        if photo:
            results.append({
                "link_id": link.id,
                "id": photo.id,
                "year": photo.year,
                "filename": photo.filename,
                "stored_path": photo.stored_path,
                "thumbnail_path": photo.thumbnail_path,
                "mime_type": photo.mime_type,
                "file_size": photo.file_size,
                "uploaded_by": photo.uploaded_by or "",
                "uploaded_at": photo.uploaded_at.isoformat() if photo.uploaded_at else "",
                "caption": link.caption or "",
                "sort_order": link.sort_order,
            })
    return results


def link_photo(photo_id: int, target_table: str, target_id: int,
               caption: str = "", sort_order: int = 0) -> dict | None:
    """Link a photo to a target entity.

    Args:
        photo_id: Photo ID.
        target_table: Target table name.
        target_id: Target record ID.
        caption: Optional caption.
        sort_order: Optional sort order.

    Returns:
        Link dict, or None if photo not found.
    """
    photo = Photo.query.get(photo_id)
    if not photo:
        return None

    link = PhotoLink(
        photo_id=photo_id,
        target_table=target_table,
        target_id=int(target_id),
        caption=caption,
        sort_order=sort_order,
    )
    db.session.add(link)
    db.session.commit()

    return {
        "id": link.id,
        "photo_id": link.photo_id,
        "target_table": link.target_table,
        "target_id": link.target_id,
        "caption": link.caption or "",
        "sort_order": link.sort_order,
    }


def unlink_photo(link_id: int) -> bool:
    """Remove a photo link.

    Args:
        link_id: PhotoLink ID.

    Returns:
        True if removed, False if not found.
    """
    link = PhotoLink.query.get(link_id)
    if not link:
        return False
    db.session.delete(link)
    db.session.commit()
    return True
