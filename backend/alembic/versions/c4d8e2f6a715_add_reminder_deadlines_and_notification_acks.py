"""add reminder_deadlines and notification_acknowledgements (iteration 3, stage 2 / F-09)

Revision ID: c4d8e2f6a715
Revises: a1c3f5e7b901
Create Date: 2026-09-19 15:00:00.000000

注意(詳細設計書4.13.1):
- 新規テーブルの追加のみ。既存テーブルの変更・再作成は行わない(既存データ・子データに影響しない)。
- 旧版の起動時create_all()で先にテーブルが作成されたDBや、再実行に備え、冪等に実装する(IF NOT EXISTS)。
- ダウングレードは提供しない。適用前のDBは起動時マイグレーションが自動で退避コピーする。
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c4d8e2f6a715'
down_revision: Union[str, None] = 'a1c3f5e7b901'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS reminder_deadlines (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            due_date TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'OTHER',
            memo TEXT,
            is_recurring INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            CONSTRAINT ck_reminder_deadlines_category CHECK (category IN ('TAX_FILING','CONTRACT_RENEWAL','OTHER')),
            CONSTRAINT ck_reminder_deadlines_is_recurring CHECK (is_recurring IN (0,1))
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_reminder_deadlines_due_date ON reminder_deadlines (due_date)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_acknowledgements (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            source_type TEXT NOT NULL,
            source_id INTEGER NOT NULL,
            acknowledged_state TEXT NOT NULL,
            acknowledged_due_date TEXT NOT NULL,
            acknowledged_at TEXT NOT NULL,
            CONSTRAINT uq_notification_ack_source UNIQUE (source_type, source_id),
            CONSTRAINT ck_notification_ack_source_type CHECK (source_type IN ('INVOICE_DUE','QUOTE_EXPIRY','PROJECT_DUE','DEADLINE')),
            CONSTRAINT ck_notification_ack_state CHECK (acknowledged_state IN ('UPCOMING','OVERDUE'))
        )
        """
    )


def downgrade() -> None:
    raise NotImplementedError("ダウングレードは提供しません(詳細設計書4.13.1)。適用前に取得したDBのコピーから復元してください。")
