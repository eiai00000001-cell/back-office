#!/bin/bash
# 起動.app から呼び出されるランチャースクリプト(詳細設計書4.7.3)。
# バックエンド(Uvicorn)をバックグラウンドで起動し、既定のブラウザを開く。
set -u

# 日本語が文字の途中で切れないよう、UTF-8ロケールを明示する(Finder起動の起動.appはロケール未設定のことがある)。
for _loc in en_US.UTF-8 ja_JP.UTF-8 C.UTF-8; do
  if locale -a 2>/dev/null | grep -qix "${_loc}"; then
    LC_ALL="${_loc}"
    break
  fi
done
export LC_ALL="${LC_ALL:-en_US.UTF-8}"
export LANG="${LC_ALL}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

HEALTH_URL="http://127.0.0.1:8000/api/health"
PID_FILE="${BACKEND_DIR}/run/uvicorn.pid"
LOG_FILE="${BACKEND_DIR}/logs/uvicorn.log"

mkdir -p "${BACKEND_DIR}/run" "${BACKEND_DIR}/logs"

log() {
  printf '%s %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$1" >>"${LOG_FILE}"
}

# ダイアログ表示。表示に失敗した場合(osascript異常終了等)もログへ記録して気付けるようにする。
notify() {
  local msg
  msg="$(printf %s "$1" | tr -d '"\\' | tr '\n' ' ')"
  if ! osascript -e "display dialog \"${msg}\" buttons {\"OK\"} default button \"OK\" with icon caution" >/dev/null 2>&1; then
    log "ダイアログの表示に失敗しました。内容: ${msg}"
  fi
}

is_healthy() {
  curl -s -o /dev/null -w "%{http_code}" "${HEALTH_URL}" 2>/dev/null | grep -q "^200$"
}

if is_healthy; then
  open "http://127.0.0.1:8000"
  exit 0
fi

cd "${BACKEND_DIR}" || exit 1

# 二重起動の排他(mkdirによる簡易ロック)。ロックにはPIDを記録し、異常終了で残った古いロックは検知して回復する。
LOCK_DIR="${BACKEND_DIR}/run/launch.lock"
HEALTH_MAX_ATTEMPTS="${LAUNCH_HEALTH_MAX_ATTEMPTS:-30}"  # 30 * 0.5秒 = 最大15秒
HEALTH_INTERVAL="${LAUNCH_HEALTH_INTERVAL:-0.5}"
HOLD_LOCK=0

LOCK_GRACE="${LAUNCH_LOCK_GRACE:-1}"                     # PID未記入のロックを古いと判定するまでの猶予(秒)
LOCK_STALE_SECONDS="${LAUNCH_LOCK_STALE_SECONDS:-300}"   # この秒数より古いロックはPIDが生存していても古いとみなす(PID再利用対策)

release_lock() {
  if [ "${HOLD_LOCK}" -eq 1 ]; then
    rm -f "${LOCK_DIR}/pid"
    rmdir "${LOCK_DIR}" 2>/dev/null
    HOLD_LOCK=0
  fi
}

# ロック(pidファイル)の経過秒数。取得できない場合は0(=新しい扱い)。
lock_age() {
  local mtime
  mtime="$(stat -f %m "${LOCK_DIR}/pid" 2>/dev/null || stat -c %Y "${LOCK_DIR}/pid" 2>/dev/null)"
  if [ -z "${mtime}" ]; then
    echo 0
  else
    echo $(($(date +%s) - mtime))
  fi
}

try_mkdir_lock() {
  if mkdir "${LOCK_DIR}" 2>/dev/null; then
    HOLD_LOCK=1
    echo $$ >"${LOCK_DIR}/pid"
    return 0
  fi
  return 1
}

# 古いロックを解除する。rename(mv)で自分専用名へ退避するため、同時に複数が試みても成功するのは1つだけ。
# 退避したものが観測したロックと別物(他者が取得し直した新しいロック)だった場合は元に戻して断念する。
remove_stale_lock() {
  local observed="$1" mine="${LOCK_DIR}.stale.$$" moved
  mv "${LOCK_DIR}" "${mine}" 2>/dev/null || return 1
  moved="$(cat "${mine}/pid" 2>/dev/null)"
  if [ "${moved}" != "${observed}" ]; then
    mv -n "${mine}" "${LOCK_DIR}" 2>/dev/null || { rm -f "${mine}/pid"; rmdir "${mine}" 2>/dev/null; }
    return 1
  fi
  rm -f "${mine}/pid"
  rmdir "${mine}" 2>/dev/null
  return 0
}

acquire_lock() {
  try_mkdir_lock && return 0
  local holder
  holder="$(cat "${LOCK_DIR}/pid" 2>/dev/null)"
  if [ -z "${holder}" ]; then
    sleep "${LOCK_GRACE}"  # 取得直後でPID書き込み前の可能性があるため、少し待って再確認する
    holder="$(cat "${LOCK_DIR}/pid" 2>/dev/null)"
  fi
  if [ -n "${holder}" ] && kill -0 "${holder}" 2>/dev/null && [ "$(lock_age)" -lt "${LOCK_STALE_SECONDS}" ]; then
    return 1  # 別の起動処理が実行中
  fi
  log "古い起動ロック(PID: ${holder:-不明})を検知したため解除します"
  remove_stale_lock "${holder}" || return 1
  try_mkdir_lock
}

trap release_lock EXIT
trap 'exit 130' INT TERM HUP

if ! acquire_lock; then
  # 別の起動処理が進行中。完了(ヘルスチェック成功)を待ってブラウザだけ開く。
  log "別の起動処理が実行中のため、この起動は待機のみ行います"
  waited=0
  while [ "${waited}" -lt "${HEALTH_MAX_ATTEMPTS}" ]; do
    if is_healthy; then
      open "http://127.0.0.1:8000"
      exit 0
    fi
    sleep "${HEALTH_INTERVAL}"
    waited=$((waited + 1))
  done
  notify "別の起動処理が完了しませんでした。logs/uvicorn.logを確認してください"
  exit 1
fi

# ロック取得前に先行プロセスが起動を完了していた場合は、2つ目のUvicornを起動せずブラウザだけ開く
# (run/uvicorn.pidの上書き防止)。
if is_healthy; then
  release_lock
  open "http://127.0.0.1:8000"
  exit 0
fi

# 起動前にDBマイグレーションを自動適用する(適用前に db/ へ退避コピーを作成。適用済みなら何もしない)。
# 標準出力(技術的詳細)はログへ、標準エラー(1行の日本語要約)のみをダイアログ用に取得する。
# 失敗した場合はアプリ本体を起動しない。
MIGRATE_ERR="$("${BACKEND_DIR}/.venv/bin/python" -m app.migrate 2>&1 >>"${LOG_FILE}")"
if [ $? -ne 0 ]; then
  log "マイグレーション失敗: ${MIGRATE_ERR}"
  REASON="$(printf %s "${MIGRATE_ERR}" | grep -v '^[[:space:]]*$' | tail -n 1 | cut -c1-200)"
  notify "データベースの更新に失敗したため起動を中止しました。${REASON} 詳細はlogs/uvicorn.logを確認してください。"
  exit 1
fi

nohup "${BACKEND_DIR}/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 >>"${LOG_FILE}" 2>&1 &
echo $! > "${PID_FILE}"

attempt=0
while [ "${attempt}" -lt "${HEALTH_MAX_ATTEMPTS}" ]; do
  if is_healthy; then
    open "http://127.0.0.1:8000"
    exit 0
  fi
  sleep "${HEALTH_INTERVAL}"
  attempt=$((attempt + 1))
done

notify "起動に失敗しました。logs/uvicorn.logを確認してください"
exit 1
