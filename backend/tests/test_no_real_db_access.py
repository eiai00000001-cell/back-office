"""テスト・import・起動がスキーマ作成等で実DBへ接触しないことの検証(README要確認事項#14)。"""
import subprocess
import sys
from pathlib import Path

from app import config
from app.database import Base
from app.migration_runner import _schema_signature, upgrade_to_head

BACKEND_DIR = Path(__file__).resolve().parents[1]
REAL_DB_PATH = BACKEND_DIR.parent / "db" / "back_office.db"


def test_suite_runs_with_guard_db_path_not_real_db():
    assert config.DB_PATH != REAL_DB_PATH
    assert not config.DB_PATH.parent.exists()  # 誤って触れれば失敗する(存在しない場所)
    assert config.SQLALCHEMY_DATABASE_URL.endswith("/nonexistent-back-office-guard/back_office.db")


def test_importing_app_main_does_not_create_db_file_or_dir(tmp_path):
    db_path = tmp_path / "sub" / "x.db"
    code = "import app.main, app.database  # noqa\nfrom app.main import app\nassert app.routes"
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=BACKEND_DIR,
        env={"BACK_OFFICE_DB_PATH": str(db_path), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert not db_path.parent.exists()  # ディレクトリもファイルも作られない


def test_new_database_is_fully_built_by_migrations_and_matches_models(tmp_path):
    """DBが無い状態から全リビジョンが通り、ORMモデル(create_all相当)と同一構造になる。"""
    from sqlalchemy import create_engine

    migrated = tmp_path / "new" / "migrated.db"
    result = upgrade_to_head(migrated)
    assert result.applied and result.backup_path is None
    ref = tmp_path / "ref.db"
    engine = create_engine(f"sqlite:///{ref}")
    Base.metadata.create_all(engine)
    engine.dispose()
    sig_m, sig_r = _schema_signature(migrated), _schema_signature(ref)
    assert set(sig_m) == set(sig_r)
    for table in sig_r:
        assert [c[:2] for c in sig_m[table][0]] == [c[:2] for c in sig_r[table][0]], table
