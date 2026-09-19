import os
import shutil
import uuid
from datetime import datetime

import pytest

# 実DB(db/back_office.db)へ接触しないための保証: appのimportより前に、DBパスを存在しない場所へ差し替える。
# テストが誤って既定のエンジン/DB_PATHを使うと「unable to open database file」で失敗する(実DBは参照されない)。
GUARD_DB_PATH = "/nonexistent-back-office-guard/back_office.db"
os.environ["BACK_OFFICE_DB_PATH"] = GUARD_DB_PATH
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import Base, create_db_engine
from app import models  # noqa: F401  (ensures all models are registered on Base)


@pytest.fixture()
def db_session() -> Session:
    engine = create_db_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    from sqlalchemy.orm import sessionmaker

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def app_client(tmp_path, monkeypatch):
    """A TestClient backed by an isolated sqlite file and attachment dir."""
    db_path = tmp_path / "test.db"
    attachments_dir = tmp_path / "attachments"

    import app.config as config

    monkeypatch.setattr(config, "DB_PATH", db_path)
    monkeypatch.setattr(config, "SQLALCHEMY_DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setattr(config, "ATTACHMENTS_DIR", attachments_dir)

    import app.database as database

    test_engine = create_db_engine(f"sqlite:///{db_path}")
    monkeypatch.setattr(database, "engine", test_engine)
    from sqlalchemy.orm import sessionmaker

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    monkeypatch.setattr(database, "SessionLocal", TestingSessionLocal)

    Base.metadata.create_all(test_engine)

    from app.main import app
    from app.database import get_db

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
    shutil.rmtree(attachments_dir, ignore_errors=True)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def unique_str(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"
