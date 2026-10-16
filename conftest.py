from config import settings
import pytest
from sqlmodel import Session, create_engine, SQLModel , delete
from fastapi.testclient import TestClient
from main import app , request_log
from database import get_session, URL

TEST_DATABASE_URL = settings.test_database_url

if TEST_DATABASE_URL is None:
    raise RuntimeError("TEST_DATABASE_URL is not set. The tests need a separate test database.")

if TEST_DATABASE_URL == settings.database_url:
    raise RuntimeError("TEST_DATABASE_URL must differ from DATABASE_URL: the tests delete rows.")

test_engine = create_engine(TEST_DATABASE_URL, echo=False)

def get_test_session():
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def client():
    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app, headers={"X-API-Key": settings.api_key}) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    request_log.clear()

    with Session(test_engine) as session:
        session.exec(delete(URL))
        session.commit()

@pytest.fixture
def anon_client():
    app.dependency_overrides[get_session] = get_test_session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    request_log.clear()
