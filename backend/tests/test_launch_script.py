"""launch.sh(指摘20・23)のスタブを使った動作テスト。実DB・実サーバーには触れない。"""
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parents[1] / "scripts" / "launch.sh"


def _exe(path: Path, body: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


@pytest.fixture()
def env(tmp_path):
    backend = tmp_path / "backend"
    (backend / "scripts").mkdir(parents=True)
    shutil.copy(SRC, backend / "scripts" / "launch.sh")
    bins = tmp_path / "bin"
    _exe(bins / "curl", 'echo 000; exit 0\n')  # 常に非healthy
    _exe(bins / "open", f'echo "$@" >> "{tmp_path}/open.log"\n')
    _exe(bins / "osascript", f'echo "$@" >> "{tmp_path}/dialog.log"\n')
    _exe(backend / ".venv/bin/uvicorn", "sleep 0\n")
    e = dict(os.environ, PATH=f"{bins}:{os.environ['PATH']}", LAUNCH_HEALTH_MAX_ATTEMPTS="2", LAUNCH_HEALTH_INTERVAL="0.05")
    return tmp_path, backend, e


def _run(backend, e):
    return subprocess.run(["bash", str(backend / "scripts" / "launch.sh")], env=e, capture_output=True, text=True, timeout=30)


def test_failure_dialog_shows_only_reason_and_points_to_log(env):
    tmp, backend, e = env
    _exe(backend / ".venv/bin/python", 'echo "INFO [alembic] noise" >&2\necho "データベースの更新に失敗しました。理由XYZ" >&2\nexit 1\n')
    r = _run(backend, e)
    assert r.returncode == 1
    dialog = (tmp / "dialog.log").read_text()
    assert "理由XYZ" in dialog and "uvicorn.log" in dialog
    assert "INFO [alembic]" not in dialog
    assert "理由XYZ" in (backend / "logs" / "uvicorn.log").read_text()
    assert not (backend / "run" / "launch.lock").exists()


def test_dialog_failure_is_logged(env):
    tmp, backend, e = env
    _exe(tmp / "bin" / "osascript", "exit 1\n")
    _exe(backend / ".venv/bin/python", 'echo "失敗理由" >&2\nexit 1\n')
    _run(backend, e)
    assert "ダイアログ" in (backend / "logs" / "uvicorn.log").read_text()


def test_stale_lock_is_recovered_and_lock_released(env):
    tmp, backend, e = env
    _exe(backend / ".venv/bin/python", "exit 0\n")
    lock = backend / "run" / "launch.lock"
    lock.mkdir(parents=True)
    (lock / "pid").write_text("999999")  # 存在しないPID
    r = _run(backend, e)
    assert "他の起動処理" not in r.stdout
    assert (backend / "logs" / "uvicorn.log").exists()
    assert not lock.exists()


def test_live_lock_blocks_second_launch(env):
    tmp, backend, e = env
    marker = tmp / "migrated"
    _exe(backend / ".venv/bin/python", f"touch {marker}\nexit 0\n")
    lock = backend / "run" / "launch.lock"
    lock.mkdir(parents=True)
    holder = subprocess.Popen(["sleep", "20"])
    try:
        (lock / "pid").write_text(str(holder.pid))
        r = _run(backend, e)
        assert not marker.exists()
        assert lock.exists()  # 他者のロックは解放しない
        assert r.returncode in (0, 1)
    finally:
        holder.kill()
