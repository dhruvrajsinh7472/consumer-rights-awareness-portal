import os
import sys
import tempfile
from pathlib import Path
import pytest

# Ensure root directory is on the Python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import create_app
from init_db import init_database

@pytest.fixture
def app():
    """Create and configure a testing Flask app instance with a temporary database."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)

    # Initialize the temporary database with foundational seed data
    init_database(db_path=db_path)

    app = create_app("testing")
    app.config.update({
        "TESTING": True,
        "DATABASE_PATH": db_path,
        "SECRET_KEY": "test-secret-key-for-pytest",
    })

    yield app

    # Cleanup temporary database file
    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def client(app):
    """Test client for simulating HTTP requests."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """CLI runner for testing commands."""
    return app.test_cli_runner()
