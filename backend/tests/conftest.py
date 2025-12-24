import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.main import app
from app.db import get_db
from app.models import Base, Reseller


@pytest.fixture(scope="session")
def db_engine():
    fd, path = tempfile.mkstemp()
    os.close(fd)
    url = f"sqlite:///{path}"
    engine = create_engine(url, future=True)
    Base.metadata.create_all(engine)
    yield engine
    os.remove(path)


@pytest.fixture(autouse=True)
def db_session(db_engine):
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine, future=True)
    db = TestingSessionLocal()
    Base.metadata.create_all(bind=db_engine)
    reseller = Reseller(name="Test Reseller", auth_username="reseller")
    db.add(reseller)
    db.commit()
    db.refresh(reseller)

    def override_get_db():
        try:
            yield db
        finally:
            db.rollback()
    app.dependency_overrides[get_db] = override_get_db
    yield db
    db.close()
    app.dependency_overrides.clear()


@pytest.fixture()
def client(db_session):
    return TestClient(app)
