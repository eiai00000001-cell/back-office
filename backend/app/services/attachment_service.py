"""領収書ファイルの検証・保存(F-02)。詳細設計書4.2章、5.2章。"""
import shutil
import uuid
from pathlib import Path

from app import config
from app.exceptions import ValidationFailedError

INVALID_FILE_MESSAGE = "対応していないファイル形式、またはサイズが上限(10MB)を超えています"


class AttachmentService:
    def __init__(self, base_dir: Path | None = None):
        # Resolved lazily (per instantiation) rather than bound at import time,
        # so that overriding app.config.ATTACHMENTS_DIR (e.g. in tests) takes effect.
        self.base_dir = base_dir if base_dir is not None else config.ATTACHMENTS_DIR

    def validate(self, filename: str, size: int) -> None:
        self._validate_filename(filename)
        extension = Path(filename).suffix.lower()
        if extension not in config.ALLOWED_ATTACHMENT_EXTENSIONS:
            raise ValidationFailedError(INVALID_FILE_MESSAGE)
        if size > config.MAX_ATTACHMENT_SIZE_BYTES:
            raise ValidationFailedError(INVALID_FILE_MESSAGE)

    @staticmethod
    def _validate_filename(filename: str) -> None:
        # パストラバーサル対策(CWE-22、レビュー指摘2対応)。クライアントが指定した
        # ファイル名に区切り文字(`/`・`\`)や`..`、NULLバイトが含まれる場合は拒否する。
        # `pathlib`のセパレータ解釈だけに頼るとOS依存(例: POSIXでは`\`は区切り文字と
        # 見なされない)になるため、文字列レベルでも明示的にチェックする。
        if not filename or "\x00" in filename or "/" in filename or "\\" in filename or ".." in filename:
            raise ValidationFailedError(INVALID_FILE_MESSAGE)
        sanitized = Path(filename).name
        if sanitized in ("", ".", "..") or sanitized != filename:
            raise ValidationFailedError(INVALID_FILE_MESSAGE)

    def save(self, expense_id: int, filename: str, content: bytes) -> str:
        expense_dir = self.base_dir / str(expense_id)
        expense_dir.mkdir(parents=True, exist_ok=True)
        # validate()を経由しない呼び出しに備え、ファイル名部分のみを取り出す(多層防御)。
        safe_filename = Path(filename).name
        stored_name = f"{uuid.uuid4()}_{safe_filename}"
        file_path = expense_dir / stored_name
        file_path.write_bytes(content)
        return f"{expense_id}/{stored_name}"

    def get_file_path(self, relative_path: str) -> Path:
        return self.base_dir / relative_path

    def delete_all(self, expense_id: int) -> None:
        """経費削除時に添付ファイル一式を削除する(レビュー指摘10対応)。"""
        expense_dir = self.base_dir / str(expense_id)
        if expense_dir.exists():
            shutil.rmtree(expense_dir, ignore_errors=True)
