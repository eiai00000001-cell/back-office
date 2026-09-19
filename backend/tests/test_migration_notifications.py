"""段階2マイグレーション(期限・確認済みテーブル追加)を段階1適用済みDBへ適用して検証する(詳細設計書4.13.1・6.5章)。"""
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.migration_runner import get_head_revision, upgrade_to_head

BACKEND_DIR = Path(__file__).resolve().parents[1]
STAGE1_REV = "a1c3f5e7b901"
STAGE2_REV = "c4d8e2f6a715"


def _config(db_path: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["database_url"] = f"sqlite:///{db_path}"
    return cfg


def _counts(conn):
    tables = ["clients", "invoices", "quotes", "expenses", "payments", "invoice_items", "quote_items", "projects"]
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}


@pytest.fixture()
def stage1_db(tmp_path):
    db_path = tmp_path / "stage1.db"
    command.upgrade(_config(db_path), STAGE1_REV)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("INSERT INTO clients (name, created_at, updated_at) VALUES ('C', 't', 't')")
    conn.execute("INSERT INTO projects (name, status, created_at, updated_at) VALUES ('P','IN_PROGRESS','t','t')")
    conn.execute(
        "INSERT INTO invoices (invoice_number, client_id, issue_date, due_date, subtotal_amount, tax_amount,"
        " total_amount, project_id, created_at, updated_at) VALUES ('2026-0001', 1, '2026-09-01', '2026-09-30', 1000, 100, 1100, 1, 't', 't')"
    )
    conn.execute(
        "INSERT INTO invoice_items (invoice_id, item_name, quantity, unit_price, tax_category, amount, sort_order)"
        " VALUES (1, 'x', 1, 1000, 'STANDARD_10', 1000, 0)"
    )
    conn.execute("INSERT INTO payments (invoice_id, payment_date, amount, created_at) VALUES (1, '2026-09-10', 500, 't')")
    conn.execute(
        "INSERT INTO expenses (expense_date, account_category, amount, tax_category, project_id, created_at, updated_at)"
        " VALUES ('2026-09-01', '雑費', 300, 'STANDARD_10', 1, 't', 't')"
    )
    conn.commit()
    conn.close()
    return db_path


def test_revision_chain_head_is_stage2():
    assert get_head_revision() == STAGE2_REV


def test_upgrade_adds_tables_and_keeps_existing_data(stage1_db):
    conn = sqlite3.connect(stage1_db)
    before = _counts(conn)
    conn.close()

    command.upgrade(_config(stage1_db), "head")

    conn = sqlite3.connect(stage1_db)
    assert _counts(conn) == before
    assert conn.execute("SELECT project_id FROM invoices").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0] == 1
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    assert {"reminder_deadlines", "notification_acknowledgements", "idx_reminder_deadlines_due_date"} <= names
    cols = {r[1] for r in conn.execute("PRAGMA table_info(reminder_deadlines)")}
    assert cols == {"id", "name", "due_date", "category", "memo", "is_recurring", "created_at", "updated_at"}
    cols = {r[1] for r in conn.execute("PRAGMA table_info(notification_acknowledgements)")}
    assert cols == {"id", "source_type", "source_id", "acknowledged_state", "acknowledged_due_date", "acknowledged_at"}
    conn.close()


def test_new_tables_enforce_constraints(stage1_db):
    command.upgrade(_config(stage1_db), "head")
    conn = sqlite3.connect(stage1_db)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO reminder_deadlines (name, due_date, category, created_at, updated_at) VALUES ('a','2026-10-01','BAD','t','t')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO reminder_deadlines (name, due_date, is_recurring, created_at, updated_at) VALUES ('a','2026-10-01',2,'t','t')"
        )
    ack = "INSERT INTO notification_acknowledgements (source_type, source_id, acknowledged_state, acknowledged_due_date, acknowledged_at) VALUES (?,?,?,?,'t')"
    conn.execute(ack, ("INVOICE_DUE", 1, "UPCOMING", "2026-09-30"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ack, ("INVOICE_DUE", 1, "OVERDUE", "2026-09-30"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ack, ("OTHER", 2, "OVERDUE", "2026-09-30"))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(ack, ("QUOTE_EXPIRY", 2, "SOON", "2026-09-30"))
    conn.close()


def test_upgrade_is_idempotent_when_tables_already_created_by_create_all(stage1_db):
    conn = sqlite3.connect(stage1_db)
    conn.execute(
        "CREATE TABLE reminder_deadlines (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, due_date TEXT NOT NULL,"
        " category TEXT NOT NULL DEFAULT 'OTHER', memo TEXT, is_recurring INTEGER NOT NULL DEFAULT 0,"
        " created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    conn.commit()
    conn.close()
    command.upgrade(_config(stage1_db), "head")
    conn = sqlite3.connect(stage1_db)
    assert conn.execute("SELECT COUNT(*) FROM notification_acknowledgements").fetchone()[0] == 0
    conn.close()


def test_startup_migration_backs_up_and_applies(stage1_db):
    result = upgrade_to_head(stage1_db)
    assert result.applied
    assert result.backup_path is not None and result.backup_path.exists()
    conn = sqlite3.connect(result.backup_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "reminder_deadlines" not in tables  # 退避コピーは適用前の状態
    conn.close()
    assert upgrade_to_head(stage1_db).applied is False  # 冪等


def test_stage1_schema_without_alembic_version_is_stamped_and_upgraded(stage1_db):
    conn = sqlite3.connect(stage1_db)
    conn.execute("DROP TABLE alembic_version")
    conn.commit()
    conn.close()
    upgrade_to_head(stage1_db)
    conn = sqlite3.connect(stage1_db)
    assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == STAGE2_REV
    assert conn.execute("SELECT COUNT(*) FROM invoices").fetchone()[0] == 1
    conn.close()


def test_existing_tables_are_not_recreated(stage1_db):
    """テーブル再作成(バッチ変更)をしていないこと: 子データ(payments等)と既存のインデックスが保たれる。"""
    conn = sqlite3.connect(stage1_db)
    idx_before = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    conn.close()
    command.upgrade(_config(stage1_db), "head")
    conn = sqlite3.connect(stage1_db)
    idx_after = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}
    assert idx_before <= idx_after
    assert conn.execute("SELECT COUNT(*) FROM invoice_items").fetchone()[0] == 1
    conn.close()


def test_startup_migration_succeeds_on_db_partially_prebuilt_by_legacy_create_all(tmp_path):
    """旧create_all由来の状態: 一部テーブル(projects・段階2の2表)が先に作成済み、alembic_versionは旧、project_id列なし。"""
    from sqlalchemy import create_engine

    from app import models  # noqa: F401
    from app.database import Base

    db_path = tmp_path / "legacy.db"
    command.upgrade(_config(db_path), "2e1e85c3b7cc")
    engine = create_engine(f"sqlite:///{db_path}")
    for name in ("projects", "reminder_deadlines", "notification_acknowledgements"):
        Base.metadata.tables[name].create(engine)
    engine.dispose()

    result = upgrade_to_head(db_path)
    assert result.applied and result.backup_path is not None and result.backup_path.exists()
    conn = sqlite3.connect(db_path)
    assert conn.execute("SELECT version_num FROM alembic_version").fetchone()[0] == get_head_revision()
    cols = {r[1] for r in conn.execute("PRAGMA table_info(invoices)")}
    assert "project_id" in cols
    conn.close()
    assert upgrade_to_head(db_path).applied is False
