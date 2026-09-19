"""起動スクリプト(launch.sh)から呼び出すマイグレーション自動適用コマンド。

使い方: python -m app.migrate  (失敗時は1行の日本語要約を標準エラー、技術的詳細を標準出力へ出力し、終了コード1で終了する)
"""
import sys

from app.migration_runner import MigrationError, upgrade_to_head


def main() -> int:
    try:
        result = upgrade_to_head()
    except MigrationError as exc:
        print(f"詳細: {exc.detail}" if exc.detail else "", file=sys.stdout)
        print(str(exc), file=sys.stderr)
        return 1
    if result.applied:
        print(f"マイグレーションを適用しました(退避コピー: {result.backup_path})")
    else:
        print("マイグレーションは適用済みです")
    return 0


if __name__ == "__main__":
    sys.exit(main())
