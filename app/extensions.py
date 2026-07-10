"""Flask extensions — initialized here, bound to app in create_app()."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "manage.login"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id: str):
    """Flask-Login user loader callback.

    Loads a User by primary key (integer id).
    Uses the dedicated User model for admin authentication,
    separate from the Member model which tracks association members.
    """
    from app.models.user import User
    return User.query.get(int(user_id))


def init_extensions(app):
    """Initialize all Flask extensions with the given app instance.

    Call this from create_app() to set up SQLAlchemy, configure
    SQLite WAL mode, and initialize Flask-Login.
    """
    db.init_app(app)
    login_manager.init_app(app)

    # Enable WAL mode for SQLite — better concurrent read performance.
    with app.app_context():
        if "sqlite" in app.config.get("SQLALCHEMY_DATABASE_URI", ""):
            from sqlalchemy import text
            db.session.execute(text("PRAGMA journal_mode=WAL"))
            db.session.execute(text("PRAGMA foreign_keys=ON"))
            db.session.commit()
