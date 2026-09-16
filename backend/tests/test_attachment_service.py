import io

import pytest

from app.exceptions import ValidationFailedError
from app.services.attachment_service import AttachmentService


class FakeUploadFile:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    def read_all(self) -> bytes:
        return self._content


class TestValidate:
    @pytest.mark.parametrize("filename", ["receipt.jpg", "receipt.jpeg", "receipt.png", "receipt.pdf"])
    def test_accepts_allowed_extensions(self, filename):
        service = AttachmentService(base_dir=None)
        service.validate(filename, size=1024)

    def test_rejects_disallowed_extension(self):
        service = AttachmentService(base_dir=None)
        with pytest.raises(ValidationFailedError):
            service.validate("receipt.txt", size=1024)

    def test_rejects_oversized_file(self):
        service = AttachmentService(base_dir=None)
        with pytest.raises(ValidationFailedError):
            service.validate("receipt.jpg", size=11 * 1024 * 1024)

    def test_accepts_file_at_exactly_the_size_limit(self):
        service = AttachmentService(base_dir=None)
        service.validate("receipt.jpg", size=10 * 1024 * 1024)


class TestSaveAndRetrieve:
    def test_save_writes_file_under_expense_directory(self, tmp_path):
        service = AttachmentService(base_dir=tmp_path)
        relative_path = service.save(expense_id=42, filename="receipt.jpg", content=b"dummy-bytes")
        assert relative_path.startswith("42/")
        saved_file = tmp_path / relative_path
        assert saved_file.exists()
        assert saved_file.read_bytes() == b"dummy-bytes"

    def test_get_file_path_resolves_absolute_path(self, tmp_path):
        service = AttachmentService(base_dir=tmp_path)
        relative_path = service.save(expense_id=1, filename="a.png", content=b"x")
        resolved = service.get_file_path(relative_path)
        assert resolved == tmp_path / relative_path


class TestValidateRejectsPathTraversal:
    """レビュー指摘2: パストラバーサル(CWE-22)対策。"""

    @pytest.mark.parametrize(
        "filename",
        [
            "../../etc/passwd.jpg",
            "../evil.png",
            "sub/dir/receipt.jpg",
            "..\\evil.jpg",
        ],
    )
    def test_rejects_filenames_containing_path_components(self, filename):
        service = AttachmentService(base_dir=None)
        with pytest.raises(ValidationFailedError):
            service.validate(filename, size=1024)

    def test_rejects_empty_filename(self):
        service = AttachmentService(base_dir=None)
        with pytest.raises(ValidationFailedError):
            service.validate("", size=1024)


class TestSaveSanitizesFilename:
    """save()自体もPath(filename).nameで防御する(多層防御、レビュー指摘2対応)。"""

    def test_save_never_writes_outside_expense_directory(self, tmp_path):
        service = AttachmentService(base_dir=tmp_path)
        relative_path = service.save(expense_id=1, filename="../../evil.jpg", content=b"payload")
        saved_file = tmp_path / relative_path
        assert saved_file.exists()
        assert saved_file.resolve().parent == (tmp_path / "1").resolve()
        assert not (tmp_path.parent / "evil.jpg").exists()


class TestDeleteAll:
    """レビュー指摘10: 経費削除時の添付ファイル実体クリーンアップ。"""

    def test_delete_all_removes_expense_directory(self, tmp_path):
        service = AttachmentService(base_dir=tmp_path)
        service.save(expense_id=7, filename="receipt.jpg", content=b"x")
        assert (tmp_path / "7").exists()
        service.delete_all(7)
        assert not (tmp_path / "7").exists()

    def test_delete_all_is_noop_when_directory_missing(self, tmp_path):
        service = AttachmentService(base_dir=tmp_path)
        service.delete_all(999)
