"""Shared pytest fixtures.

SCAFFOLD - add `pytest` to requirements (dev) when the testing rotation starts.
Run with:  cd backend && ./venv/bin/python -m pytest
"""
# TODO(tests):
# import pytest
# from fastapi.testclient import TestClient
# from sqlalchemy import create_engine
# from sqlalchemy.orm import sessionmaker
# from app.database import Base, get_db
# from app.main import app
#
# @pytest.fixture()
# def client():
#     """TestClient wired to a fresh in-memory SQLite DB per test."""
#     engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
#     Base.metadata.create_all(bind=engine)
#     TestSession = sessionmaker(bind=engine)
#     app.dependency_overrides[get_db] = lambda: (yield TestSession())
#     yield TestClient(app)
#     app.dependency_overrides.clear()
