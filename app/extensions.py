"""Flask extensions — initialized here, bound to app in create_app()."""
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "manage.login"
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id: str):
    """Flask-Login user loader callback."""
    from app.models.member import Member
    return Member.query.get(int(user_id))
