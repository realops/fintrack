import pytest
from app import app as flask_app, db

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    # Set testing config
    flask_app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': True,  # Enable CSRF protection for testing
        'SECRET_KEY': 'test-secret-key'
    })
    
    # Create context and database tables
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        # Clean up after test
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create a test CLI runner for the app."""
    return app.test_cli_runner() 