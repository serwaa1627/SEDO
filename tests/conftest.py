import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from sqlalchemy.pool import StaticPool
from app import app, db, limiter


@pytest.fixture
def client():
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    # StaticPool ensures all connections share the same in-memory DB (needed for cross-context DB writes)
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        'connect_args': {'check_same_thread': False},
        'poolclass': StaticPool,
    }
    app.config['WTF_CSRF_ENABLED'] = False
    limiter.enabled = False  # Disable rate limiting so login attempts don't accumulate across tests

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

    limiter.enabled = True
