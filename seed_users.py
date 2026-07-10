"""Seed database with default admin and operator users.

Run from the project root:
    uv run python seed_users.py

Default credentials:
    admin / admin123  (系統管理員)
    user  / user123   (操作員)
"""

from app import create_app
from app.extensions import db
from app.models.user import User


def seed():
    """Create default users if they don't already exist."""
    app = create_app()
    with app.app_context():
        db.create_all()

        # Admin user
        if not User.query.filter_by(username="admin").first():
            admin = User(
                username="admin",
                display_name="系統管理員",
                role="admin",
            )
            admin.set_password("admin123")
            db.session.add(admin)
            print("  ✓ Created admin user (admin / admin123)")
        else:
            print("  - Admin user already exists, skipping")

        # Operator user
        if not User.query.filter_by(username="user").first():
            user = User(
                username="user",
                display_name="操作員",
                role="user",
            )
            user.set_password("user123")
            db.session.add(user)
            print("  ✓ Created operator user (user / user123)")
        else:
            print("  - Operator user already exists, skipping")

        db.session.commit()
        print("\n✅ Users seeded successfully!")


if __name__ == "__main__":
    seed()
