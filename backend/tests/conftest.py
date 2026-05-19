import sys
import os
import tempfile
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, DatabaseManager, init_db


@pytest.fixture
def db_manager():
    tmp_db = Path(tempfile.gettempdir()) / f"test_ssp_{uuid.uuid4().hex[:8]}.db"
    db = DatabaseManager(str(tmp_db))
    db.create_tables()
    yield db
    try:
        db.engine.dispose()
    except Exception:
        pass
    try:
        if tmp_db.exists():
            tmp_db.unlink()
    except Exception:
        pass


@pytest.fixture
def client(db_manager):
    from main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def sample_user(db_manager):
    user = db_manager.create_user("测试用户")
    return user
