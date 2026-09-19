"""レポート出力(F-10)API。詳細設計書4.11.1章・7章。生成したバイト列をそのまま返す(サーバーに保存しない)。"""
import re
from datetime import date
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Response

from app.core.constants import REPORT_MAX_MONTHS, REPORT_MAX_YEAR, REPORT_MIN_YEAR
from app.dependencies import get_report_service
from app.exceptions import UnprocessableError
from app.services.report_service import ReportService
from app.utils.date_range import build_last_12_months, period_to_dates

router = APIRouter(prefix="/api/reports", tags=["reports"])

_PERIOD_PATTERN = re.compile(r"(\d{4})-(0[1-9]|1[0-2])")
PERIOD_FORMAT_MESSAGE = "年月はYYYY-MM形式で指定してください"
PERIOD_YEAR_MESSAGE = f"期間の年は{REPORT_MIN_YEAR}〜{REPORT_MAX_YEAR}の範囲で指定してください"
PERIOD_LIMIT_MESSAGE = f"期間は最大{REPORT_MAX_MONTHS}か月(10年)以内で指定してください"


def _check_period(value: str) -> str:
    if not _PERIOD_PATTERN.fullmatch(value):
        raise UnprocessableError(PERIOD_FORMAT_MESSAGE)
    return value


def _check_year(value: str) -> str:
    if not REPORT_MIN_YEAR <= int(value[:4]) <= REPORT_MAX_YEAR:
        raise UnprocessableError(PERIOD_YEAR_MESSAGE)
    return value


def _month_count(start: str, end: str) -> int:
    return (int(end[:4]) - int(start[:4])) * 12 + (int(end[5:7]) - int(start[5:7])) + 1


@router.get("/{report_type}")
def export_report(
    report_type: str,
    period_from: str | None = None,
    period_to: str | None = None,
    fmt: str = Query("csv", alias="format"),
    service: ReportService = Depends(get_report_service),
):
    # 指定がない場合は、現在月を含む直近12ヶ月(4.8.1と同じ算出)
    default_months = build_last_12_months(date.today())
    # 判定順: 形式 → 年範囲(補完前) → 片方のみ指定の補完 → 開始>終了 → 上限(詳細設計書4.11.1)
    if period_from:
        _check_period(period_from)
    if period_to:
        _check_period(period_to)
    if period_from:
        _check_year(period_from)
    if period_to:
        _check_year(period_to)
    start = period_from or default_months[0]
    end = period_to or default_months[-1]
    if start > end:
        raise UnprocessableError("開始年月は終了年月以前を指定してください")
    if _month_count(start, end) > REPORT_MAX_MONTHS:
        raise UnprocessableError(PERIOD_LIMIT_MESSAGE)
    date_from, date_to = period_to_dates(start, end)
    report = service.generate(report_type, date_from, date_to, fmt)
    return Response(
        content=report.content,
        media_type=report.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(report.filename)}",
            "X-Record-Count": str(report.record_count),
        },
    )
