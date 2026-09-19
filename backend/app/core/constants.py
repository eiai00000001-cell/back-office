"""アプリケーション共通の定数(詳細設計書4.9.1章)。"""

# 納期・期限が「近い」とみなす日数(F-08の表示とF-09の通知で共用。★21)
NOTIFICATION_LEAD_DAYS = 7

# ホームの通知エリアに表示する件数(詳細設計書4.10.6。機能仕様書F-06の仮置き値を設計で確定)
HOME_NOTIFICATION_LIMIT = 5

# レポート出力の期間検証(詳細設計書4.11.1)
REPORT_MIN_YEAR = 2000
REPORT_MAX_YEAR = 2099
REPORT_MAX_MONTHS = 120
