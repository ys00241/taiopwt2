"""
寶榮堂花炮會管理系統 (taiopwt2) — Flask Application Package.

A modular Flask application for managing the Po Wong Tong Firecracker
Association (寶榮堂花炮會), including pre-event preparation, live-event
payment tracking, financial management, and photo gallery features.
"""

from flask import Flask
from config import config_by_name


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

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name["default"]))

    # Initialize extensions
    from app.extensions import db, login_manager

    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    _register_blueprints(app)

    # Register error handlers
    _register_error_handlers(app)

    # Context processors
    @app.context_processor
    def inject_globals():
        return {"app_version": app.config.get("VERSION", "v2.0.0")}

    return app


def _register_blueprints(app: Flask) -> None:
    """Register all application blueprints."""
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

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(members_bp)
    app.register_blueprint(items_bp)
    app.register_blueprint(editions_bp)
    app.register_blueprint(bids_bp)
    app.register_blueprint(pl_bp)
    app.register_blueprint(pre_event_bp)
    app.register_blueprint(live_event_bp)
    app.register_blueprint(manage_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(cashbook_bp)
    app.register_blueprint(photos_bp)


def _register_error_handlers(app: Flask) -> None:
    """Register application-wide error handlers."""
    from flask import render_template

    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template("errors/500.html"), 500
