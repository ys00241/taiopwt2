"""
寶榮堂花炮會管理系統 (taiopwt2) — Flask Application Package.

A modular Flask application for managing the Po Wong Tong Firecracker
Association (寶榮堂花炮會), including pre-event preparation, live-event
payment tracking, financial management, and photo gallery features.
"""

from flask import Flask
from config import config_by_name
from app.extensions import db, login_manager


def create_app(config_name: str | None = None) -> Flask:
    """Application factory.

    Creates and configures a Flask application instance with all
    registered blueprints and extensions.

    Args:
        config_name: Name of the configuration to use (development,
                     production). Defaults to the FLASK_ENV environment
                     variable or "development".

    Returns:
        Configured Flask application instance.
    """
    if config_name is None:
        import os
        config_name = os.environ.get("FLASK_ENV", "development")

    flask_app = Flask(__name__)
    flask_app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Initialize extensions (with WAL mode for SQLite)
    db.init_app(flask_app)
    login_manager.init_app(flask_app)

    # Enable WAL mode + foreign keys for SQLite
    with flask_app.app_context():
        if "sqlite" in flask_app.config.get("SQLALCHEMY_DATABASE_URI", ""):
            from sqlalchemy import text
            try:
                db.session.execute(text("PRAGMA journal_mode=WAL"))
                db.session.execute(text("PRAGMA foreign_keys=ON"))
                db.session.commit()
            except Exception:
                pass  # non-SQLite or first-run

    # Import models so they are registered with SQLAlchemy
    with flask_app.app_context():
        import app.models  # noqa: F401
    
    # Auto-create all tables if they don't exist (fresh DB)
    with flask_app.app_context():
        db.create_all()
        db.session.commit()

    # Migrate existing database — add new columns if they don't exist
    with flask_app.app_context():
        if "sqlite" in flask_app.config.get("SQLALCHEMY_DATABASE_URI", ""):
            from sqlalchemy import text as _t
            # First check if members table exists
            import sqlalchemy as sa
            inspector = sa.inspect(db.engine)
            tables = inspector.get_table_names()
            if "members" in tables:
                cols = [c["name"] for c in inspector.get_columns("members")]
                for col, col_type in [
                    ("member_type", "VARCHAR(20) DEFAULT 'member'"),
                    ("status", "VARCHAR(20) DEFAULT 'active'"),
                    ("name_alais", "VARCHAR(200)"),
                    ("group_name", "VARCHAR(200)"),
                    ("referrer", "VARCHAR(200)"),
                    ("end_year", "INTEGER"),
                    ("bad_debt", "BOOLEAN DEFAULT 0"),
                ]:
                    if col not in cols:
                        try:
                            db.session.execute(_t(f"ALTER TABLE members ADD COLUMN {col} {col_type}"))
                        except Exception:
                            pass
                db.session.commit()
            # membership_fees table
            if "membership_fees" not in tables:
                try:
                    db.session.execute(_t("""
                        CREATE TABLE IF NOT EXISTS membership_fees (
                            id VARCHAR PRIMARY KEY,
                            member_id VARCHAR NOT NULL REFERENCES members(id),
                            year INTEGER NOT NULL,
                            amount FLOAT DEFAULT 0,
                            payment_method VARCHAR(50) DEFAULT 'cash',
                            handler VARCHAR(100),
                            notes TEXT,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """))
                    db.session.execute(_t("""
                        CREATE INDEX IF NOT EXISTS idx_membership_fees_member
                        ON membership_fees(member_id)
                    """))
                    db.session.commit()
                except Exception:
                    pass

    # Register blueprints
    _register_blueprints(flask_app)

    # Register error handlers
    _register_error_handlers(flask_app)

    # Context processors
    @flask_app.context_processor
    def inject_globals():
        from datetime import datetime
        from app.extensions import db
        from app.models.this_year_item import ThisYearItem
        from app.models.bid import Bid
        from app.models.edition import Edition
        from app.models.pl import PL

        # Gather all distinct years from DB tables that have a 'year' column
        years = set()
        try:
            for model in (ThisYearItem, Bid, Edition, PL):
                rows = db.session.query(model.year).distinct().all()
                years.update(r[0] for r in rows if r[0] is not None)
        except Exception:
            pass  # Fall back to just current_year if DB not ready

        all_years = sorted(years, reverse=True) if years else [datetime.now().year]

        return {
            "app_version": flask_app.config.get("VERSION", "v2.1.0"),
            "current_year": datetime.now().year,
            "all_years": all_years,
        }

    return flask_app


def _register_blueprints(flask_app: Flask) -> None:
    """Register all application blueprints.

    URL prefix strategy:
    - Blueprints that define their own ``url_prefix`` in the constructor
      (cashbook=/cashbook, pre_event=/pre, live_event=/live, manage=/manage,
       photos=/photos) are registered WITHOUT an extra prefix.
    - Blueprints whose routes embed the path directly
      (dashboard=/, members=/members, items=/items, editions=/editions,
       bids=/bids, pl=/pl) are registered at ``/``.
    - The api blueprint is registered at ``/api``.
    """
    from app.blueprints.dashboard import bp as dashboard_bp
    from app.blueprints.members import bp as members_bp
    from app.blueprints.items import bp as items_bp
    from app.blueprints.editions import bp as editions_bp
    from app.blueprints.bids import bp as bids_bp
    from app.blueprints.pl import bp as pl_bp
    from app.blueprints.pre_event import bp as pre_event_bp
    from app.blueprints.live_event import bp as live_event_bp
    from app.blueprints.manage import bp as manage_bp
    from app.blueprints.api import bp as api_bp
    from app.blueprints.cashbook import bp as cashbook_bp
    from app.blueprints.photos import bp as photos_bp

    flask_app.register_blueprint(dashboard_bp)     # url_prefix='/' (implied)
    flask_app.register_blueprint(members_bp)       # routes at /members
    flask_app.register_blueprint(items_bp)         # routes at /items
    flask_app.register_blueprint(editions_bp)      # routes at /editions
    flask_app.register_blueprint(bids_bp)          # routes at /bids
    flask_app.register_blueprint(pl_bp)            # routes at /pl
    flask_app.register_blueprint(pre_event_bp)     # url_prefix='/pre' (from bp)
    flask_app.register_blueprint(live_event_bp)    # url_prefix='/live' (from bp)
    flask_app.register_blueprint(manage_bp)        # url_prefix='/manage' (from bp)
    flask_app.register_blueprint(api_bp, url_prefix="/api")
    flask_app.register_blueprint(cashbook_bp)      # url_prefix='/cashbook' (from bp)
    flask_app.register_blueprint(photos_bp)        # url_prefix='/photos' (from bp)


def _register_error_handlers(flask_app: Flask) -> None:
    """Register application-wide error handlers."""
    from flask import render_template

    @flask_app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @flask_app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500

    @flask_app.errorhandler(403)
    def forbidden(e):
        return render_template("errors/403.html"), 403
