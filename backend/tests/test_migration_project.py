"""段階1マイグレーション(案件テーブル+project_id列追加)を既存データ入りDBへ適用して検証する(詳細設計書4.13.1)。"""
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_REV = "a1c3f5e7b901"
PREV_REV = "2e1e85c3b7cc"


def _config(db_path: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["database_url"] = f"sqlite:///{db_path}"
    return cfg


def _counts(conn):
    tables = ["invoices", "quotes", "expenses", "payments", "invoice_items", "quote_items"]
    return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in tables}


@pytest.fixture()
def migrated_old_db(tmp_path):
    db_path = tmp_path / "old.db"
    cfg = _config(db_path)
    command.upgrade(cfg, PREV_REV)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("INSERT INTO clients (name, created_at, updated_at) VALUES ('C', 't', 't')")
    conn.execute(
        "INSERT INTO invoices (invoice_number, client_id, issue_date, due_date, subtotal_amount, tax_amount,"
        " total_amount, created_at, updated_at) VALUES ('2026-0001', 1, '2026-09-01', '2026-09-30', 1000, 100, 1100, 't', 't')"
    )
    conn.execute(
        "INSERT INTO invoice_items (invoice_id, item_name, quantity, unit_price, tax_category, amount, sort_order)"
        " VALUES (1, 'x', 1, 1000, 'STANDARD_10', 1000, 0)"
    )
    conn.execute("INSERT INTO payments (invoice_id, payment_date, amount, created_at) VALUES (1, '2026-09-10', 500, 't')")
    conn.execute(
        "INSERT INTO quotes (quote_number, client_id, status, subtotal_amount, tax_amount, total_amount, created_at, updated_at)"
        " VALUES ('2026-0001', 1, 'DRAFT', 1000, 100, 1100, 't', 't')"
    )
    conn.execute(
        "INSERT INTO expenses (expense_date, account_category, amount, tax_category, created_at, updated_at)"
        " VALUES ('2026-09-01', '雑費', 300, 'STANDARD_10', 't', 't')"
    )
    conn.commit()
    conn.close()
    return db_path


def test_upgrade_preserves_existing_data_and_adds_null_project_id(migrated_old_db):
    conn = sqlite3.connect(migrated_old_db)
    before = _counts(conn)
    sums_before = conn.execute("SELECT SUM(total_amount) FROM invoices").fetchone()[0]
    conn.close()

    command.upgrade(_config(migrated_old_db), "head")

    conn = sqlite3.connect(migrated_old_db)
    assert _counts(conn) == before
    assert conn.execute("SELECT SUM(total_amount) FROM invoices").fetchone()[0] == sums_before
    for table in ("invoices", "quotes", "expenses"):
        cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]
        assert "project_id" in cols
        assert conn.execute(f"SELECT COUNT(*) FROM {table} WHERE project_id IS NOT NULL").fetchone()[0] == 0
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master")}
    assert {"projects", "idx_projects_status", "idx_projects_client_id", "idx_projects_due_date",
            "idx_invoices_project_id", "idx_quotes_project_id", "idx_expenses_project_id"} <= names
    conn.close()


def test_upgrade_is_idempotent_when_projects_table_already_created_by_create_all(migrated_old_db):
    conn = sqlite3.connect(migrated_old_db)
    conn.execute(
        "CREATE TABLE projects (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, client_id INTEGER,"
        " status TEXT NOT NULL DEFAULT 'NOT_STARTED', due_date TEXT, description TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)"
    )
    conn.commit()
    conn.close()
    command.upgrade(_config(migrated_old_db), "head")
    conn = sqlite3.connect(migrated_old_db)
    assert "project_id" in [r[1] for r in conn.execute("PRAGMA table_info(invoices)")]
    conn.close()


def test_project_delete_sets_null_and_keeps_children_after_migration(migrated_old_db):
    command.upgrade(_config(migrated_old_db), "head")
    conn = sqlite3.connect(migrated_old_db)
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("INSERT INTO projects (name, status, created_at, updated_at) VALUES ('P','NOT_STARTED','t','t')")
    conn.execute("UPDATE invoices SET project_id = 1")
    conn.execute("DELETE FROM projects WHERE id = 1")
    conn.commit()
    assert conn.execute("SELECT project_id FROM invoices").fetchone()[0] is None
    assert conn.execute("SELECT COUNT(*) FROM invoice_items").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0] == 1
    conn.close()


def _api_snapshot(client):
    paths = [
        "/api/home/summary",
        "/api/dashboard/sales-and-payments",
        "/api/dashboard/expenses",
        "/api/dashboard/profit-loss",
        "/api/dashboard/quotes",
    ]
    snapshot = {}
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, path
        snapshot[path] = response.json()
    return snapshot


def _use_db(app_client, db_path: Path):
    from sqlalchemy.orm import sessionmaker

    from app.database import create_db_engine, get_db

    engine = create_db_engine(f"sqlite:///{db_path}")
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = session_factory()
        try:
            yield db
            db.commit()
        finally:
            db.close()

    app_client.app.dependency_overrides[get_db] = override_get_db
    return engine


def test_home_summary_and_dashboard_are_unchanged_by_migration(migrated_old_db, tmp_path, app_client):
    """詳細設計書4.13.1-6: 適用前後でF-07(ダッシュボード)・home/summaryの集計結果が一致すること。

    適用前スキーマのDBは新モデル(project_idあり)のORMでは読めないため、適用前と同一データを
    新スキーマ(create_all)のDBへコピーした基準DBと、マイグレーション適用後のDBの応答を比較する。
    """
    from app.database import Base, create_db_engine

    reference = tmp_path / "reference.db"
    ref_engine = create_db_engine(f"sqlite:///{reference}")
    Base.metadata.create_all(ref_engine)
    ref_engine.dispose()
    conn = sqlite3.connect(reference)
    conn.execute("ATTACH DATABASE ? AS old", (str(migrated_old_db),))
    for table in ("clients", "company_profile", "invoices", "invoice_items", "payments", "quotes", "quote_items", "expenses"):
        cols = [r[1] for r in conn.execute(f"PRAGMA old.table_info({table})")]
        col_list = ", ".join(cols)
        conn.execute(f"INSERT OR REPLACE INTO main.{table} ({col_list}) SELECT {col_list} FROM old.{table}")
    conn.commit()
    conn.execute("DETACH DATABASE old")
    conn.close()

    command.upgrade(_config(migrated_old_db), "head")

    engine = _use_db(app_client, reference)
    expected = _api_snapshot(app_client)
    engine.dispose()
    engine = _use_db(app_client, migrated_old_db)
    actual = _api_snapshot(app_client)
    engine.dispose()
    assert actual == expected
    assert actual["/api/home/summary"] != {}
