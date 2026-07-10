"""Application configuration — loaded from environment with sensible defaults."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "")
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'data' / 'paopao.db'}",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    # Paths
    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    CSV_EXPORT_FOLDER = str(BASE_DIR / "csv_exports")
    UPLOADS_DIR = str(BASE_DIR / "uploads")
    CSV_EXPORTS_DIR = str(BASE_DIR / "csv_exports")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB

    VERSION = "v2.0.0"


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
