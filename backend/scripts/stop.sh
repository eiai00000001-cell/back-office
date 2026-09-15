#!/bin/bash
# 終了.app から呼び出されるストップスクリプト(詳細設計書4.7.4)。
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PID_FILE="${BACKEND_DIR}/run/uvicorn.pid"

notify() {
  osascript -e "display dialog \"$1\" buttons {\"OK\"} default button \"OK\"" >/dev/null 2>&1
}

if [ -f "${PID_FILE}" ]; then
  PID="$(cat "${PID_FILE}")"
  if [ -n "${PID}" ] && kill -0 "${PID}" 2>/dev/null; then
    kill -TERM "${PID}"
    rm -f "${PID_FILE}"
    notify "システムを終了しました"
    exit 0
  fi
fi

notify "システムは起動していません"
rm -f "${PID_FILE}"
exit 0
