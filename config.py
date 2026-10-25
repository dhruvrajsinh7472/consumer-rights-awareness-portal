import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

class Config:
    """Base application configuration."""
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-cep-consumer-rights-awareness-portal")
    PROJECT_TITLE = "Technology for Consumer Rights Awareness"
    PORTAL_NAME = "Consumer Rights Awareness Portal"
    ORGANIZATION = "Community Engagement Project (CEP)"
    DATABASE_PATH = os.environ.get("DATABASE_PATH") or str(BASE_DIR / "instance" / "consumer_rights.db")
    DATABASE_URL = os.environ.get("DATABASE_URL", None)
    DATA_DIR = str(BASE_DIR / "data")
    TESTING = False
    DEBUG = False

    # Session and Cookie Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS

    # Administrative Dashboard Credentials (disabled by default unless explicitly configured)
    ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", None)
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", None)

class DevelopmentConfig(Config):
    """Development configuration with debugging enabled."""
    DEBUG = True

class TestingConfig(Config):
    """Testing configuration with dedicated test database."""
    TESTING = True
    DEBUG = True
    DATABASE_PATH = str(BASE_DIR / "instance" / "test_consumer_rights.db")
    DATABASE_URL = None

class ProductionConfig(Config):
    """Production configuration for Render & Supabase PostgreSQL."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    DATABASE_URL = os.environ.get("DATABASE_URL")

config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
