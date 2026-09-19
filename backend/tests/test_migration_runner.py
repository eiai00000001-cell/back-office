"""起動時マイグレーション自動適用(app.migration_runner)のテスト。"""
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.migration_runner import MigrationError, get_head_revision, upgrade_to_head

BACKEND_DIR = Path(__file__).resolve().parents[1]
PREV_REV = "2e1e85c3b7cc"


def _cfg(db_path: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["database_url"] = f"sqlite:///{db_path}"
    return cfg


def _current(db_path: Path):
    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute("SELECT version_num FROM alembic_version").fetchone()
        return row[0] if row else None
    finally:
        conn.close()


@pytest.fixture()
def old_db(tmp_path):
    db_path = tmp_path / "back_office.db"
    command.upgrade(_cfg(db_path), PREV_REV)
    conn = sqlite3.connect(db_path)
    conn.execute("INSERT INTO clients (name, created_at, updated_at) VALUES ('C', 't', 't')")
    conn.commit()
    conn.close()
    return db_path


def test_applies_pending_migration_and_creates_backup(old_db):
    result = upgrade_to_head(old_db)
    head = get_head_revision()
    assert _current(old_db) == head
    backup = old_db.with_name(f"{old_db.name}.before-{head}")
    assert backup.exists()
    assert _current(backup) == PREV_REV
    assert result.applied is True
    assert result.backup_path == backup


def test_idempotent_when_already_at_head(old_db):
    upgrade_to_head(old_db)
    result = upgrade_to_head(old_db)
    assert result.applied is False
    assert result.backup_path is None


def test_existing_backup_is_not_overwritten(old_db):
    head = get_head_revision()
    backup = old_db.with_name(f"{old_db.name}.before-{head}")
    backup.write_bytes(b"keep me")
    upgrade_to_head(old_db)
    assert backup.read_bytes() == b"keep me"
    assert _current(old_db) == head


def test_new_database_is_created_without_backup(tmp_path):
    db_path = tmp_path / "new.db"
    result = upgrade_to_head(db_path)
    assert _current(db_path) == get_head_revision()
    assert result.backup_path is None


def test_failure_raises_japanese_error_and_keeps_backup(old_db, monkeypatch):
    from app import migration_runner

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(migration_runner.command, "upgrade", boom)
    with pytest.raises(MigrationError) as exc:
        upgrade_to_head(old_db)
    assert "マイグレーション" in str(exc.value)
    assert "退避" in str(exc.value)
    assert _current(old_db) == PREV_REV


def test_cli_returns_nonzero_and_japanese_message_on_failure(tmp_path, monkeypatch, capsys):
    from app import migrate

    def fail(*args):
        raise MigrationError("データベースの更新に失敗しました")

    monkeypatch.setattr(migrate, "upgrade_to_head", fail)
    assert migrate.main() == 1
    assert "失敗" in capsys.readouterr().err


# --- 指摘20〜22: 追加テスト ---


def _create_all_db(db_path: Path):
    from sqlalchemy import create_engine

    from app import models  # noqa: F401
    from app.database import Base

    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    engine.dispose()


def test_create_all_db_without_alembic_version_is_stamped_then_upgraded(tmp_path):
    db_path = tmp_path / "legacy.db"
    _create_all_db(db_path)
    result = upgrade_to_head(db_path)
    head = get_head_revision()
    assert _current(db_path) == head
    assert result.applied is True
    backup = db_path.with_name(f"{db_path.name}.before-{head}")
    assert backup.exists()


def test_old_schema_without_alembic_version_is_stamped_to_matching_revision(old_db):
    conn = sqlite3.connect(old_db)
    conn.execute("DROP TABLE alembic_version")
    conn.commit()
    conn.close()
    upgrade_to_head(old_db)
    assert _current(old_db) == get_head_revision()
    conn = sqlite3.connect(old_db)
    assert conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0] == 1
    assert "projects" in {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()


def test_unknown_schema_without_alembic_version_is_not_touched(tmp_path):
    db_path = tmp_path / "odd.db"
    _create_all_db(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute("ALTER TABLE clients ADD COLUMN extra_col TEXT")
    conn.commit()
    conn.close()
    with pytest.raises(MigrationError) as exc:
        upgrade_to_head(db_path)
    assert "alembic_version" in str(exc.value)
    assert "一致" in str(exc.value)
    conn = sqlite3.connect(db_path)
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    conn.close()
    assert "alembic_version" not in tables


def test_incomplete_backup_is_not_treated_as_existing(old_db, monkeypatch):
    from app import migration_runner

    head = get_head_revision()
    backup = old_db.with_name(f"{old_db.name}.before-{head}")
    real_copy = migration_runner._copy_db

    def partial_copy(src, dst):
        Path(dst).write_bytes(b"partial")
        raise OSError("disk full")

    monkeypatch.setattr(migration_runner, "_copy_db", partial_copy)
    with pytest.raises(MigrationError):
        upgrade_to_head(old_db)
    assert not backup.exists()
    assert _current(old_db) == PREV_REV

    monkeypatch.setattr(migration_runner, "_copy_db", real_copy)
    upgrade_to_head(old_db)
    assert _current(backup) == PREV_REV


def test_error_message_is_single_line_and_detail_is_separate(old_db, monkeypatch):
    from app import migration_runner

    def boom(*args, **kwargs):
        raise RuntimeError("line1\nline2")

    monkeypatch.setattr(migration_runner.command, "upgrade", boom)
    with pytest.raises(MigrationError) as exc:
        upgrade_to_head(old_db)
    assert "\n" not in str(exc.value)
    assert "line1" in exc.value.detail


def test_cli_prints_summary_to_stderr_and_detail_to_stdout(monkeypatch, capsys):
    from app import migrate

    def fail(*args):
        raise MigrationError("要約です", detail="詳細です\nINFO xxx")

    monkeypatch.setattr(migrate, "upgrade_to_head", fail)
    assert migrate.main() == 1
    out = capsys.readouterr()
    assert out.err.strip() == "要約です"
    assert "詳細です" in out.out


# --- 指摘27 ---


def _sig_of(tmp_path, name, ddl):
    from app.migration_runner import _schema_signature

    path = tmp_path / name
    conn = sqlite3.connect(path)
    conn.execute(ddl)
    conn.commit()
    conn.close()
    return _schema_signature(path)


def test_signature_distinguishes_column_default(tmp_path):
    a = _sig_of(tmp_path, "a.db", "CREATE TABLE t (id INTEGER PRIMARY KEY, s TEXT DEFAULT 'x')")
    b = _sig_of(tmp_path, "b.db", "CREATE TABLE t (id INTEGER PRIMARY KEY, s TEXT DEFAULT 'y')")
    assert a != b


def test_signature_distinguishes_unique_constraint(tmp_path):
    a = _sig_of(tmp_path, "a.db", "CREATE TABLE t (id INTEGER PRIMARY KEY, s TEXT UNIQUE)")
    b = _sig_of(tmp_path, "b.db", "CREATE TABLE t (id INTEGER PRIMARY KEY, s TEXT)")
    assert a != b


def test_upgrade_failure_after_stamp_explains_restore(tmp_path, monkeypatch):
    from app import migration_runner

    db_path = tmp_path / "legacy.db"
    _create_all_db(db_path)
    real_upgrade = migration_runner.command.upgrade

    def upgrade(cfg, rev):
        if str(db_path) in cfg.attributes["database_url"]:  # 参照DBでの照合は実物、対象DBへの適用のみ失敗させる
            raise RuntimeError("boom")
        return real_upgrade(cfg, rev)

    monkeypatch.setattr(migration_runner.command, "upgrade", upgrade)
    with pytest.raises(MigrationError) as exc:
        upgrade_to_head(db_path)
    msg = str(exc.value)
    assert "\n" not in msg
    assert "stamp" in msg and "復元" in msg and ".before-" in msg
