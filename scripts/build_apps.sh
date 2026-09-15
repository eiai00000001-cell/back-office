#!/bin/bash
# 起動.app / 終了.app を生成するビルドスクリプト(詳細設計書4.7.5、初回セットアップ時のみ実行)。
set -eu

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${PROJECT_ROOT}/dist"

build_app() {
  local app_name="$1"       # 例: 起動.app
  local executable_name="$2" # launcher / stopper
  local target_script="$3"   # backend/scripts/launch.sh など

  local app_dir="${DIST_DIR}/${app_name}"
  local contents_dir="${app_dir}/Contents"
  local macos_dir="${contents_dir}/MacOS"

  mkdir -p "${macos_dir}"

  cat > "${contents_dir}/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleExecutable</key>
  <string>${executable_name}</string>
  <key>CFBundleName</key>
  <string>${app_name%.app}</string>
  <key>CFBundleIdentifier</key>
  <string>com.eiaitec.backoffice.${executable_name}</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>1.0</string>
  <key>LSUIElement</key>
  <true/>
</dict>
</plist>
PLIST

  cat > "${macos_dir}/${executable_name}" <<WRAPPER
#!/bin/bash
exec "${PROJECT_ROOT}/${target_script}"
WRAPPER

  chmod +x "${macos_dir}/${executable_name}"
  echo "generated: ${app_dir}"
}

mkdir -p "${DIST_DIR}"
build_app "起動.app" "launcher" "backend/scripts/launch.sh"
build_app "終了.app" "stopper" "backend/scripts/stop.sh"

echo "完了しました。${DIST_DIR} 配下の 起動.app / 終了.app を、デスクトップ等の使いやすい場所へコピーしてください。"
