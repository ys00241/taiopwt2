"""Manage blueprint — 系統管理 (login, settings, database, import/export)."""
from flask import Blueprint, render_template
from flask_login import login_required, login_user, logout_user, current_user

bp = Blueprint("manage", __name__,
               url_prefix="/manage")


# ── Allowed tables ──
EXPORT_TABLES = {
    "members", "editions", "items", "bids", "pl",
    "this_year_items", "expenses", "sponsors",
    "live_income", "daily_entries",
}
IMPORT_TABLES = {
    "members", "this_year_items", "expenses",
    "sponsors", "live_income",
}
TABLE_MODELS = {}


def _get_model(table_name):
    """Lazy-load SQLAlchemy model class for a given table name."""
    if table_name in TABLE_MODELS:
        return TABLE_MODELS[table_name]
    from app.models.member import Member
    from app.models.edition import Edition
    from app.models.item import Item
    from app.models.bid import Bid
    from app.models.pl import PL
    from app.models.this_year_item import ThisYearItem
    from app.models.expense import Expense
    from app.models.sponsor import Sponsor
    from app.models.live_income import LiveIncome
    from app.models.daily_entry import DailyEntry

    mapping = {
        "members": Member,
        "editions": Edition,
        "items": Item,
        "bids": Bid,
        "pl": PL,
        "this_year_items": ThisYearItem,
        "expenses": Expense,
        "sponsors": Sponsor,
        "live_income": LiveIncome,
        "daily_entries": DailyEntry,
    }
    TABLE_MODELS.update(mapping)
    return mapping.get(table_name)


def _get_model_columns(model):
    """Return list of column names (excluding the primary key 'id' and relation cols)."""
    return [c.name for c in model.__table__.columns]


def _serialize_row(model, row):
    """Convert a model row to a dict for CSV export, handling special types."""
    import datetime
    data = {}
    for col in model.__table__.columns:
        val = getattr(row, col.name)
        if isinstance(val, datetime.date):
            val = val.isoformat()
        elif isinstance(val, datetime.datetime):
            val = val.strftime("%Y-%m-%d %H:%M:%S")
        elif val is None:
            val = ""
        data[col.name] = val
    return data


# ════════════════════════════════════════════════════════════
#  Auth routes
# ════════════════════════════════════════════════════════════

@bp.route("/login", methods=["GET", "POST"])
def login():
    """User login page — authenticate with username + password."""
    from flask import render_template, request, redirect, url_for, flash

    # If already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if not username or not password:
            flash("請輸入用戶名稱及密碼", "error")
            return render_template("login.html")

        from app.models.user import User
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("用戶名稱或密碼不正確", "error")
            return render_template("login.html")

        if not user.is_active:
            flash("此帳戶已被停用", "error")
            return render_template("login.html")

        remember = request.form.get("remember") == "1"
        login_user(user, remember=remember)
        flash(f"歡迎回來，{user.display_name or user.username}！", "info")

        next_page = request.args.get("next")
        if next_page:
            return redirect(next_page)
        return redirect(url_for("dashboard.dashboard"))

    return render_template("login.html")


@bp.route("/logout")
def logout():
    """User logout — clear session and redirect to login."""
    from flask import redirect, url_for, flash
    logout_user()
    flash("已成功登出", "info")
    return redirect(url_for("manage.login"))


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """System settings — change password."""
    from flask import render_template, request, redirect, url_for, flash
    from app.extensions import db

    if request.method == "POST":
        current_password = request.form.get("current_password", "")
        new_password = request.form.get("new_password", "")
        confirm_password = request.form.get("confirm_password", "")

        if not current_password or not new_password:
            flash("請填寫所有密碼欄位", "error")
            return render_template("manage/settings.html")

        if not current_user.check_password(current_password):
            flash("當前密碼不正確", "error")
            return render_template("manage/settings.html")

        if new_password != confirm_password:
            flash("新密碼與確認密碼不一致", "error")
            return render_template("manage/settings.html")

        if len(new_password) < 4:
            flash("新密碼長度至少需要4個字符", "error")
            return render_template("manage/settings.html")

        current_user.set_password(new_password)
        db.session.commit()
        flash("密碼已成功更新", "info")
        return redirect(url_for("manage.settings"))

    return render_template("manage/settings.html")


@bp.route("/db-status")
@login_required
def db_status():
    """Database status / admin panel."""
    from flask import jsonify
    return jsonify({"ok": True})


# ════════════════════════════════════════════════════════════
#  New routes
# ════════════════════════════════════════════════════════════

@bp.route("")
@login_required
def index():
    """Management hub page — links to import/export/backup/restore."""
    from flask import render_template
    return render_template(
        "manage/index.html",
        export_tables=sorted(EXPORT_TABLES),
        import_tables=sorted(IMPORT_TABLES),
    )


# ──────────────────────────────────────────────────────────
#  CSV Export per table
# ──────────────────────────────────────────────────────────

@bp.route("/export/<table_name>")
@login_required
def export_table_csv(table_name):
    """Export a table as CSV, with optional year filter."""
    from flask import request, Response
    from app.extensions import db
    import csv
    import io

    if table_name not in EXPORT_TABLES:
        return Response(f"Table '{table_name}' not allowed for export.", status=400)

    model = _get_model(table_name)
    if model is None:
        return Response(f"Unknown table: {table_name}", status=400)

    query = model.query

    # Apply year filter if the model has a 'year' column
    year = request.args.get("year", type=int)
    if year is not None and hasattr(model, "year"):
        query = query.filter(model.year == year)

    rows = query.order_by(model.__table__.primary_key.columns.keys()[0]).all()
    columns = [c.name for c in model.__table__.columns]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        data = _serialize_row(model, row)
        writer.writerow([data.get(col, "") for col in columns])

    output.seek(0)
    filename = f"{table_name}"
    if year:
        filename += f"_{year}"
    filename += ".csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv; charset=utf-8-sig",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ──────────────────────────────────────────────────────────
#  CSV Import per table
# ──────────────────────────────────────────────────────────

@bp.route("/import/<table_name>", methods=["POST"])
@login_required
def import_table_csv(table_name):
    """Import a CSV file into the given table."""
    from flask import request, jsonify
    from app.extensions import db

    # Admin-only check
    if current_user.role != "admin":
        return jsonify({"ok": False, "error": "僅管理員可執行匯入操作"}), 403

    if table_name not in IMPORT_TABLES:
        return jsonify({"ok": False, "error": f"Table '{table_name}' not allowed for import."}), 400

    model = _get_model(table_name)
    if model is None:
        return jsonify({"ok": False, "error": f"Unknown table: {table_name}"}), 400

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "error": "Empty filename."}), 400

    import csv
    import io

    stream = io.StringIO(file.stream.read().decode("utf-8-sig"))
    reader = csv.DictReader(stream)

    if reader.fieldnames is None:
        return jsonify({"ok": False, "error": "Empty or invalid CSV."}), 400

    columns = [c.name for c in model.__table__.columns]
    fieldnames = [f for f in reader.fieldnames if f in columns]

    count = 0
    errors = []
    for row_idx, row in enumerate(reader, 2):
        try:
            kwargs = {k: (v if v != "" else None) for k, v in row.items() if k in fieldnames}
            # Try to convert numeric fields
            for col in model.__table__.columns:
                if col.name in kwargs and kwargs[col.name] is not None:
                    val = kwargs[col.name]
                    if isinstance(col.type, (db.Integer,)):
                        try:
                            kwargs[col.name] = int(val)
                        except (ValueError, TypeError):
                            pass
                    elif isinstance(col.type, (db.Float,)):
                        try:
                            kwargs[col.name] = float(val)
                        except (ValueError, TypeError):
                            pass
            instance = model(**kwargs)
            db.session.add(instance)
            count += 1
        except Exception as e:
            db.session.rollback()
            errors.append(f"Row {row_idx}: {e}")
            # Re-begin a session transaction
            continue

    if count > 0:
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return jsonify({"ok": False, "error": f"Commit failed: {e}"}), 500

    return jsonify({
        "ok": True,
        "imported": count,
        "errors": errors,
        "table": table_name,
    })


# ──────────────────────────────────────────────────────────
#  Full Backup (ZIP: DB + all CSVs)
# ──────────────────────────────────────────────────────────

@bp.route("/backup")
@login_required
def backup_zip():
    """Download a ZIP containing the SQLite DB file and all tables as CSV."""
    from flask import Response, current_app, jsonify
    from app.extensions import db
    import csv
    import io
    import os
    import zipfile

    # Admin-only check
    if current_user.role != "admin":
        return jsonify({"ok": False, "error": "僅管理員可執行備份操作"}), 403

    buf = io.BytesIO()

    # Determine the SQLite database path
    db_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    db_path = db_uri.replace("sqlite:///", "")
    if not os.path.isabs(db_path):
        db_path = os.path.join(current_app.root_path, db_path)

    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:

        # 1. Include the database file
        if os.path.exists(db_path):
            zf.write(db_path, os.path.basename(db_path))

        # 2. Include each table as CSV
        for table_name in sorted(EXPORT_TABLES):
            model = _get_model(table_name)
            if model is None:
                continue
            rows = model.query.order_by(
                model.__table__.primary_key.columns.keys()[0]
            ).all()
            columns = [c.name for c in model.__table__.columns]

            csv_buf = io.StringIO()
            writer = csv.writer(csv_buf)
            writer.writerow(columns)
            for row in rows:
                data = _serialize_row(model, row)
                writer.writerow([data.get(col, "") for col in columns])

            csv_buf.seek(0)
            zf.writestr(f"{table_name}.csv", csv_buf.getvalue())

    buf.seek(0)
    return Response(
        buf.getvalue(),
        mimetype="application/zip",
        headers={"Content-Disposition": 'attachment; filename="taio_backup.zip"'},
    )


# ──────────────────────────────────────────────────────────
#  ZIP Restore
# ──────────────────────────────────────────────────────────

@bp.route("/restore", methods=["POST"])
@login_required
def restore_zip():
    """Upload a ZIP backup to restore the database and/or CSV data."""
    from flask import request, jsonify
    from app.extensions import db
    import csv
    import io
    import zipfile
    import tempfile
    import os
    import shutil

    # Admin-only check
    if current_user.role != "admin":
        return jsonify({"ok": False, "error": "僅管理員可執行還原操作"}), 403

    if "file" not in request.files:
        return jsonify({"ok": False, "error": "No file uploaded."}), 400

    file = request.files["file"]
    if file.filename == "":
        return jsonify({"ok": False, "error": "Empty filename."}), 400

    results = {"ok": True, "tables_restored": [], "tables_skipped": [], "errors": []}

    with zipfile.ZipFile(file, "r") as zf:
        # Check for SQLite DB in the zip
        db_candidates = [n for n in zf.namelist() if n.endswith(".db")]
        if db_candidates:
            db_filename = db_candidates[0]
            # Extract DB to a temp location
            tmp_dir = tempfile.mkdtemp()
            try:
                zf.extract(db_filename, tmp_dir)
                extracted_db = os.path.join(tmp_dir, db_filename)
                # We can't easily replace a live DB, but we note it
                results["db_file_found"] = db_filename
                results["db_file_size"] = os.path.getsize(extracted_db)
            finally:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        # Process CSV files
        for name in zf.namelist():
            if not name.endswith(".csv"):
                continue
            table_name = name.replace(".csv", "")
            if table_name not in IMPORT_TABLES:
                results["tables_skipped"].append(table_name)
                continue

            model = _get_model(table_name)
            if model is None:
                results["tables_skipped"].append(table_name)
                continue

            try:
                content = zf.read(name).decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(content))
                if reader.fieldnames is None:
                    results["errors"].append(f"{name}: empty/invalid CSV")
                    continue

                columns = [c.name for c in model.__table__.columns]
                fieldnames = [f for f in reader.fieldnames if f in columns]

                count = 0
                for row in reader:
                    kwargs = {k: (v if v != "" else None) for k, v in row.items() if k in fieldnames}
                    # Type coercion
                    for col in model.__table__.columns:
                        if col.name in kwargs and kwargs[col.name] is not None:
                            val = kwargs[col.name]
                            if isinstance(col.type, (db.Integer,)):
                                try:
                                    kwargs[col.name] = int(val)
                                except (ValueError, TypeError):
                                    pass
                            elif isinstance(col.type, (db.Float,)):
                                try:
                                    kwargs[col.name] = float(val)
                                except (ValueError, TypeError):
                                    pass
                    instance = model(**kwargs)
                    db.session.add(instance)
                    count += 1

                db.session.commit()
                results["tables_restored"].append({"table": table_name, "rows": count})

            except Exception as e:
                db.session.rollback()
                results["errors"].append(f"{name}: {e}")
                continue

    return jsonify(results)


# ════════════════════════════════════════════════════════════
#  Category Management — Item & Expense categories (JSON)
# ════════════════════════════════════════════════════════════

import json
from pathlib import Path


def _get_categories_path(cat_type: str) -> Path:
    """Return the JSON file path for the given category type."""
    from flask import current_app
    data_dir = Path(current_app.root_path) / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / f"{cat_type}_categories.json"


def _load_categories(cat_type: str) -> list:
    """Load categories from JSON file."""
    path = _get_categories_path(cat_type)
    if not path.exists():
        # Return defaults based on type
        defaults = {
            "item": ["花炮", "神像", "祭品", "裝飾", "食品", "飲品", "用品", "其他"],
            "expense": [
                "酒席", "場地", "佈置", "音響", "攝影",
                "神料", "花炮", "樂隊", "歌星", "舞獅",
                "工作人員", "雜項", "交通", "宣傳", "保險",
            ],
        }
        return defaults.get(cat_type, [])
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def _save_categories(cat_type: str, categories: list) -> None:
    """Save categories to JSON file."""
    path = _get_categories_path(cat_type)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)


@bp.route("/categories")
@login_required
def categories():
    """Category management page — manage item & expense categories."""
    item_cats = _load_categories("item")
    expense_cats = _load_categories("expense")
    return render_template(
        "manage/categories.html",
        item_categories=item_cats,
        expense_categories=expense_cats,
    )


@bp.route("/categories/add/<type>", methods=["POST"])
@login_required
def categories_add(type):
    """Add a new category (type=item or expense)."""
    from flask import request, jsonify

    if type not in ("item", "expense"):
        return jsonify({"ok": False, "error": "Invalid category type"}), 400

    cat = request.form.get("category", "").strip()
    if not cat:
        return jsonify({"ok": False, "error": "Category name is required"}), 400

    cats = _load_categories(type)
    if cat in cats:
        return jsonify({"ok": False, "error": "Category already exists"}), 400

    cats.append(cat)
    _save_categories(type, cats)
    return jsonify({"ok": True, "categories": cats})


@bp.route("/categories/remove/<type>", methods=["POST"])
@login_required
def categories_remove(type):
    """Remove a category by index (type=item or expense)."""
    from flask import request, jsonify

    if type not in ("item", "expense"):
        return jsonify({"ok": False, "error": "Invalid category type"}), 400

    try:
        index = int(request.form.get("index", -1))
    except (ValueError, TypeError):
        return jsonify({"ok": False, "error": "Invalid index"}), 400

    cats = _load_categories(type)
    if index < 0 or index >= len(cats):
        return jsonify({"ok": False, "error": "Index out of range"}), 400

    removed = cats.pop(index)
    _save_categories(type, cats)
    return jsonify({"ok": True, "removed": removed, "categories": cats})
