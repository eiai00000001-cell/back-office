"""Application-wide path configuration.

Paths are resolved relative to this file so that behavior does not depend on
the current working directory the server happens to be started from.
"""
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

DB_DIR = PROJECT_ROOT / "db"
DB_PATH = DB_DIR / "back_office.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

DATA_DIR = PROJECT_ROOT / "data"
ATTACHMENTS_DIR = DATA_DIR / "attachments" / "expenses"

STATIC_DIR = BACKEND_DIR / "static"

MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_ATTACHMENT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
