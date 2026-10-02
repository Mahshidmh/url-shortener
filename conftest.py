from config import settings
import pytest
from sqlmodel import Session, create_engine, SQLModel , delete
from fastapi.testclient import TestClient
from main import app , request_log
from database import get_session, URL

TEST_DATABASE_URL = "postgresql://shortener_user:mysecretpassword@db:5432/shortener_test_db"
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
