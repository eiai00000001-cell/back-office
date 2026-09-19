"""起動時にAlembicマイグレーションを自動適用する(適用前に対象DBを退避コピー)。"""
import os
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine

from app.config import BACKEND_DIR, DB_PATH


class MigrationError(Exception):
    """マイグレーションの適用に失敗した場合の例外。

    メッセージは利用者向けの1行の日本語要約。技術的な詳細(複数行可)は`detail`に保持する(ログ用)。
    """

    def __init__(self, message: str, detail: str = ""):
        super().__init__(message)
        self.detail = detail


@dataclass
class MigrationResult:
    applied: bool
    backup_path: Path | None = None


def _alembic_config(db_path: Path) -> Config:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    cfg.attributes["database_url"] = f"sqlite:///{db_path}"
    cfg.attributes["configure_logger"] = False  # alembicのINFOログで利用者向け表示を汚さない
    return cfg


def get_head_revision() -> str:
    return ScriptDirectory.from_config(_alembic_config(DB_PATH)).get_current_head()


def _current_revision(db_path: Path) -> str | None:
    engine = create_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            return MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()


def _copy_db(src_path: Path, dst_path: Path) -> None:
    src = sqlite3.connect(src_path)
    dst = sqlite3.connect(dst_path)
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()


def _backup(db_path: Path, tag: str) -> Path:
    """一時名へコピーし、成功後にリネームする(途中失敗で不完全なコピーが完成品扱いされない)。"""
    backup_path = db_path.with_name(f"{db_path.name}.before-{tag}")
    if backup_path.exists():
        return backup_path  # 既存の退避コピーは上書きしない
    tmp_path = db_path.with_name(f"{backup_path.name}.tmp")
    tmp_path.unlink(missing_ok=True)  # 前回の中断で残った一時ファイルを除去
    _copy_db(db_path, tmp_path)
    os.replace(tmp_path, backup_path)
    return backup_path


def _norm_type(decl: str) -> str:
    """モデル(VARCHAR)とマイグレーション(TEXT)の表記差を吸収する(SQLiteでは同じTEXT親和性)。"""
    t = decl.upper().split("(")[0].strip()
    return "TEXT" if t in ("VARCHAR", "CHAR", "STRING", "TEXT", "CLOB") else t


def _schema_signature(db_path: Path) -> dict:
    """テーブル・列・外部キー・インデックスの構造を比較用に取り出す(alembic_versionは除く)。

    比較対象: 列(名・型・NOT NULL・既定値・主キー)、外部キー(参照先・ON DELETE)、UNIQUE(列の組)、明示インデックス。
    比較対象外: CHECK制約、ON UPDATE、トリガ(PRAGMAで取得できない/表記差が大きいため)。
    """
    conn = sqlite3.connect(db_path)
    try:
        tables = [
            r[0]
            for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' AND name != 'alembic_version'"
            )
        ]
        sig = {}
        for t in sorted(tables):
            cols = sorted((c[1], _norm_type(c[2]), c[3], c[4], c[5]) for c in conn.execute(f'PRAGMA table_info("{t}")'))
            fks = sorted((f[2], f[3], f[4], f[6].upper()) for f in conn.execute(f'PRAGMA foreign_key_list("{t}")'))
            idx = []
            uniques = []
            for i in conn.execute(f'PRAGMA index_list("{t}")').fetchall():
                if i[2] and i[3] != "pk":  # UNIQUE(制約・明示インデックスのいずれも列の組で比較)
                    uniques.append(tuple(c[2] for c in conn.execute(f'PRAGMA index_info("{i[1]}")')))
                if i[3] == "c":  # 明示作成のインデックスのみ(制約由来の自動インデックスは除く)
                    cols_i = tuple(c[2] for c in conn.execute(f'PRAGMA index_info("{i[1]}")'))
                    idx.append((i[1], i[2], cols_i))
            sig[t] = (cols, fks, sorted(idx), sorted(uniques))
        return sig
    finally:
        conn.close()


def _has_user_tables(db_path: Path) -> bool:
    return bool(_schema_signature(db_path))


def _find_matching_revision(db_path: Path) -> str | None:
    """現在のスキーマと一致する既知リビジョンを返す(新しい方を優先。一致なしはNone)。"""
    script = ScriptDirectory.from_config(_alembic_config(db_path))
    actual = _schema_signature(db_path)
    for rev in script.walk_revisions():  # head -> base の順
        with tempfile.TemporaryDirectory() as tmp:
            ref = Path(tmp) / "ref.db"
            command.upgrade(_alembic_config(ref), rev.revision)
            if _schema_signature(ref) == actual:
                return rev.revision
    return None


def upgrade_to_head(db_path: Path = DB_PATH) -> MigrationResult:
    """未適用のマイグレーションがあれば退避コピー後に適用する。適用済みなら何もしない(冪等)。

    alembic_versionが無くテーブルだけ存在するDB(create_all()のみで作成)は、スキーマが既知リビジョンと
    一致すると確認できた場合に限り、退避コピー後にstampしてからupgradeする。
    """
    head = ScriptDirectory.from_config(_alembic_config(db_path)).get_current_head()
    existed = db_path.exists()
    backup_path: Path | None = None
    stamp_rev: str | None = None
    try:
        if existed:
            current = _current_revision(db_path)
            if current == head:
                return MigrationResult(applied=False)
            if current is None and _has_user_tables(db_path):
                stamp_rev = _find_matching_revision(db_path)
                if stamp_rev is None:
                    raise MigrationError(
                        "データベースに更新履歴(alembic_version)がなく、構造も既知の版と一致しないため、"
                        "自動更新を行いませんでした。データベースは変更していません。サポートへご連絡ください。",
                        detail=f"schema mismatch: {db_path}",
                    )
            backup_path = _backup(db_path, head)
            if stamp_rev is not None:
                command.stamp(_alembic_config(db_path), stamp_rev)
        else:
            db_path.parent.mkdir(parents=True, exist_ok=True)
        command.upgrade(_alembic_config(db_path), "head")
    except MigrationError:
        raise
    except Exception as exc:
        if backup_path and stamp_rev is not None:
            hint = (
                "更新履歴の登録(stamp)は済んでいますが更新は完了していません。"
                f"アプリを停止したうえで、適用前の退避コピー({backup_path})をデータベースファイルへ上書きコピーして復元し、"
                "サポートへご連絡ください。"
            )
        elif backup_path:
            hint = f"適用前の退避コピー({backup_path})から復元できます。"
        else:
            hint = "データベースファイルは退避コピー前のため変更されていません。"
        raise MigrationError(
            f"データベースのマイグレーション(更新)に失敗しました。{hint}",
            detail=str(exc),
        ) from exc
    return MigrationResult(applied=True, backup_path=backup_path)
