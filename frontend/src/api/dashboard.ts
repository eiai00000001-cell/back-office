import { apiClient } from './client'
import type {
  DashboardExpenseSummary,
  ProfitLossSummary,
  QuoteStatusSummary,
  SalesAndPaymentsSummary,
} from '../types'

// 財務ダッシュボード(F-07、SC-12)。区画ごとに独立した4本のAPIを呼び出す(詳細設計書3.12章・4.8章)。
export const dashboardApi = {
  salesAndPayments: async (): Promise<SalesAndPaymentsSummary> =>
    (await apiClient.get('/dashboard/sales-and-payments')).data,
  expenses: async (): Promise<DashboardExpenseSummary> => (await apiClient.get('/dashboard/expenses')).data,
  profitLoss: async (): Promise<ProfitLossSummary> => (await apiClient.get('/dashboard/profit-loss')).data,
  quotes: async (): Promise<QuoteStatusSummary> => (await apiClient.get('/dashboard/quotes')).data,
}
