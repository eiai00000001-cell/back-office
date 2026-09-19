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
    e = dict(os.environ, PATH=f"{bins}:{os.environ['PATH']}", LAUNCH_HEALTH_MAX_ATTEMPTS="2", LAUNCH_HEALTH_INTERVAL="0.05", LAUNCH_LOCK_GRACE="0.5")
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


# --- 指摘24〜26 ---


def test_lock_without_pid_yet_is_not_treated_as_stale(env):
    """mkdir直後でPID未記入のロックは、猶予内にPIDが書かれれば有効なロックとして扱う(指摘24-1)。"""
    tmp, backend, e = env
    marker = tmp / "migrated"
    _exe(backend / ".venv/bin/python", f"touch {marker}\nexit 0\n")
    lock = backend / "run" / "launch.lock"
    lock.mkdir(parents=True)
    holder = subprocess.Popen(["sleep", "20"])
    writer = subprocess.Popen(["bash", "-c", f"sleep 0.2; echo {holder.pid} > {lock}/pid"])
    try:
        _run(backend, e)
        assert not marker.exists()
        assert lock.exists()
    finally:
        writer.wait()
        holder.kill()


def test_concurrent_launches_on_stale_lock_migrate_only_once(env):
    """古いロックを複数が同時に検知しても、取得できるのは1つだけ(指摘24-2)。"""
    tmp, backend, e = env
    log = tmp / "migrated.log"
    _exe(backend / ".venv/bin/python", f"echo x >> {log}\nsleep 1.5\nexit 0\n")
    lock = backend / "run" / "launch.lock"
    lock.mkdir(parents=True)
    (lock / "pid").write_text("999999")
    script = str(backend / "scripts" / "launch.sh")
    procs = [subprocess.Popen(["bash", script], env=e, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(5)]
    for p in procs:
        p.wait(timeout=30)
    assert len(log.read_text().split()) == 1
    assert not lock.exists()


def test_live_pid_but_old_lock_is_treated_as_stale(env):
    """PIDが再利用されていてもロックが期限より古ければ古いロックとして回復する(指摘24-3)。"""
    tmp, backend, e = env
    marker = tmp / "migrated"
    _exe(backend / ".venv/bin/python", f"touch {marker}\nexit 0\n")
    lock = backend / "run" / "launch.lock"
    lock.mkdir(parents=True)
    holder = subprocess.Popen(["sleep", "20"])
    try:
        pid_file = lock / "pid"
        pid_file.write_text(str(holder.pid))
        os.utime(pid_file, (1_000_000_000, 1_000_000_000))
        e["LAUNCH_LOCK_STALE_SECONDS"] = "60"
        _run(backend, e)
        assert marker.exists()
        assert not lock.exists()
    finally:
        holder.kill()


def test_healthy_after_lock_acquired_skips_second_uvicorn(env):
    """ロック取得直後にヘルスチェックが成功したら、起動せずブラウザだけ開く(指摘25)。"""
    tmp, backend, e = env
    marker = tmp / "migrated"
    started = tmp / "uvicorn_started"
    _exe(backend / ".venv/bin/python", f"touch {marker}\nexit 0\n")
    _exe(backend / ".venv/bin/uvicorn", f"touch {started}\n")
    _exe(
        tmp / "bin" / "curl",
        f'n=$(cat {tmp}/cnt 2>/dev/null || echo 0); n=$((n+1)); echo $n > {tmp}/cnt; '
        'if [ $n -ge 2 ]; then echo 200; else echo 000; fi\n',
    )
    r = _run(backend, e)
    assert r.returncode == 0
    assert "127.0.0.1:8000" in (tmp / "open.log").read_text()
    assert not marker.exists() and not started.exists()
    assert not (backend / "run" / "uvicorn.pid").exists()
    assert not (backend / "run" / "launch.lock").exists()


def test_long_japanese_reason_is_not_cut_mid_character_under_c_locale(env):
    """LC_ALL=Cで起動されても、日本語の要約が文字の途中で切れない(指摘26)。"""
    tmp, backend, e = env
    e["LC_ALL"] = "C"
    e["LANG"] = "C"
    _exe(backend / ".venv/bin/python", 'echo "' + "あ" * 150 + '" >&2\nexit 1\n')
    _run(backend, e)
    dialog = (tmp / "dialog.log").read_bytes()
    dialog.decode("utf-8")  # 不正なバイト列があれば例外
    assert "あ".encode() * 10 in dialog
