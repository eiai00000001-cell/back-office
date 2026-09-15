#!/bin/bash
# 起動.app から呼び出されるランチャースクリプト(詳細設計書4.7.3)。
# バックエンド(Uvicorn)をバックグラウンドで起動し、既定のブラウザを開く。
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

HEALTH_URL="http://127.0.0.1:8000/api/health"
PID_FILE="${BACKEND_DIR}/run/uvicorn.pid"
LOG_FILE="${BACKEND_DIR}/logs/uvicorn.log"

mkdir -p "${BACKEND_DIR}/run" "${BACKEND_DIR}/logs"

notify() {
  osascript -e "display dialog \"$1\" buttons {\"OK\"} default button \"OK\" with icon caution" >/dev/null 2>&1
}

is_healthy() {
  curl -s -o /dev/null -w "%{http_code}" "${HEALTH_URL}" 2>/dev/null | grep -q "^200$"
}

if is_healthy; then
  open "http://127.0.0.1:8000"
  exit 0
fi

cd "${BACKEND_DIR}" || exit 1
nohup "${BACKEND_DIR}/.venv/bin/uvicorn" app.main:app --host 127.0.0.1 --port 8000 >>"${LOG_FILE}" 2>&1 &
echo $! > "${PID_FILE}"

attempt=0
max_attempts=30  # 30 * 0.5秒 = 最大15秒
while [ "${attempt}" -lt "${max_attempts}" ]; do
  if is_healthy; then
    open "http://127.0.0.1:8000"
    exit 0
  fi
  sleep 0.5
  attempt=$((attempt + 1))
done

notify "起動に失敗しました。logs/uvicorn.logを確認してください"
exit 1
