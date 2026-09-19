"""Application-wide path configuration.

Paths are resolved relative to this file so that behavior does not depend on
the current working directory the server happens to be started from.
"""
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent

# BACK_OFFICE_DB_PATHでDBファイルの場所を差し替えられる(テストが実DBへ接触しないための仕組み)。
DB_PATH = Path(os.environ.get("BACK_OFFICE_DB_PATH") or PROJECT_ROOT / "db" / "back_office.db")
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_PATH}"

DATA_DIR = PROJECT_ROOT / "data"
ATTACHMENTS_DIR = DATA_DIR / "attachments" / "expenses"

STATIC_DIR = BACKEND_DIR / "static"

MAX_ATTACHMENT_SIZE_BYTES = 10 * 1024 * 1024
ALLOWED_ATTACHMENT_EXTENSIONS = {".jpg", ".jpeg", ".png", ".pdf"}
