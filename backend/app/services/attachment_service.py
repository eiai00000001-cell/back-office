"""領収書ファイルの検証・保存(F-02)。詳細設計書4.2章、5.2章。"""
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
        extension = Path(filename).suffix.lower()
        if extension not in config.ALLOWED_ATTACHMENT_EXTENSIONS:
            raise ValidationFailedError(INVALID_FILE_MESSAGE)
        if size > config.MAX_ATTACHMENT_SIZE_BYTES:
            raise ValidationFailedError(INVALID_FILE_MESSAGE)

    def save(self, expense_id: int, filename: str, content: bytes) -> str:
        expense_dir = self.base_dir / str(expense_id)
        expense_dir.mkdir(parents=True, exist_ok=True)
        stored_name = f"{uuid.uuid4()}_{filename}"
        file_path = expense_dir / stored_name
        file_path.write_bytes(content)
        return f"{expense_id}/{stored_name}"

    def get_file_path(self, relative_path: str) -> Path:
        return self.base_dir / relative_path
