"""add projects table and project_id columns (iteration 3, stage 1 / F-08)

Revision ID: a1c3f5e7b901
Revises: 2e1e85c3b7cc
Create Date: 2026-09-19 10:00:00.000000

注意(詳細設計書4.13.1):
- invoices/quotes/expenses への列追加は op.batch_alter_table(テーブル再作成)を使わず、
  ALTER TABLE ... ADD COLUMN の直接SQLで行う。SQLiteのテーブル再作成は外部キー有効時に
  invoice_items / payments の子データを削除する恐れがあるため。
- 既存行の project_id はNULLのまま(データの自動紐付けは行わない)。
- 旧版の起動時create_all()で先に projects が作成されたDBや、再実行に備え、冪等に実装する。
- ダウングレードは提供しない。適用前に db/back_office.db を手動コピーしておくこと。
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c3f5e7b901'
down_revision: Union[str, None] = '2e1e85c3b7cc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TARGET_TABLES = ("invoices", "quotes", "expenses")


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not inspector.has_table("projects"):
        op.execute(
            """
            CREATE TABLE projects (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                client_id INTEGER REFERENCES clients(id),
                status TEXT NOT NULL DEFAULT 'NOT_STARTED',
                due_date TEXT,
                description TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                CONSTRAINT ck_projects_status CHECK (status IN ('NOT_STARTED','IN_PROGRESS','WAITING_REVIEW','DONE'))
            )
            """
        )
    op.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects (status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_projects_client_id ON projects (client_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_projects_due_date ON projects (due_date)")

    for table in TARGET_TABLES:
        columns = {c["name"] for c in inspector.get_columns(table)}
        if "project_id" not in columns:
            op.execute(
                f"ALTER TABLE {table} ADD COLUMN project_id INTEGER REFERENCES projects(id) ON DELETE SET NULL"
            )
        op.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_project_id ON {table} (project_id)")


def downgrade() -> None:
    raise NotImplementedError("ダウングレードは提供しません(詳細設計書4.13.1)。適用前に取得したDBのコピーから復元してください。")
