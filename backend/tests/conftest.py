import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import engine, SessionLocal, get_db
from app.main import app


@pytest.fixture(scope="session")
def db_engine():
    return engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Provides a transactional database session for testing.
    Rolls back any changes at the end of each test to keep DB clean.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    TestClient that overrides the get_db dependency with our rollback-isolated session.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
