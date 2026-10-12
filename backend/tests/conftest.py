import os
import sys
import shutil
import tempfile
import pytest
from pathlib import Path

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Redirect settings paths to an isolated test folder BEFORE any tests or routers run
_temp_dir = tempfile.mkdtemp(prefix="insurewise_test_")
_temp_path = Path(_temp_dir)

from config import settings

settings.STORAGE_DIR = _temp_path
settings.UPLOADS_DIR = _temp_path / "uploads"
settings.INDEXES_DIR = _temp_path / "indexes"
settings.REPORTS_DIR = _temp_path / "reports"
settings.DB_PATH = _temp_path / "test_insurewise.db"

os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
os.makedirs(settings.INDEXES_DIR, exist_ok=True)
os.makedirs(settings.REPORTS_DIR, exist_ok=True)

from db import init_db
init_db()


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_env():
    yield
    try:
        shutil.rmtree(_temp_dir, ignore_errors=True)
    except Exception:
        pass
