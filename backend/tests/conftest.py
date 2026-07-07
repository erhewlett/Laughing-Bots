"""Shared pytest fixtures: a TestClient backed by a fresh in-memory DB per test.

Run with:  cd backend && ./venv/bin/python -m pytest
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    # StaticPool + a single shared connection so the request thread that
    # TestClient runs on sees the same in-memory database as the test body.
    # Without StaticPool each connection gets its own empty DB and queries
    # fail with "no such table".
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session: Session = TestSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    def _get_test_db():
        yield db_session

    app.dependency_overrides[get_db] = _get_test_db
    # Plain TestClient (no context manager) so the app lifespan does not run
    # create_all against the real engine or touch the real database file.
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        app.dependency_overrides.clear()
