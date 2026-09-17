"""財務ダッシュボード(F-07、イテレーション2)API。詳細設計書5.1章・7章・4.8章。

区画ごとに4本のエンドポイントに分割する。理由は4.8.6章参照(1本に統合すると、いずれか1区画の
集計処理で例外が発生した際に他区画分のデータも巻き込んでエラーになってしまうため)。
"""
from fastapi import APIRouter, Depends

from app.dependencies import get_dashboard_service
from app.schemas.dashboard import (
    DashboardExpenseSummaryResponse,
    ProfitLossSummaryResponse,
    QuoteStatusSummaryResponse,
    SalesAndPaymentsSummaryResponse,
)
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/sales-and-payments", response_model=SalesAndPaymentsSummaryResponse)
def get_sales_and_payments(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_sales_and_payments_summary()


@router.get("/expenses", response_model=DashboardExpenseSummaryResponse)
def get_expenses(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_expense_summary()


@router.get("/profit-loss", response_model=ProfitLossSummaryResponse)
def get_profit_loss(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_profit_loss_summary()


@router.get("/quotes", response_model=QuoteStatusSummaryResponse)
def get_quotes(service: DashboardService = Depends(get_dashboard_service)):
    return service.get_quote_status_summary()
