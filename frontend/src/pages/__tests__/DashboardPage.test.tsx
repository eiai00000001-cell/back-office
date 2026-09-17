import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DashboardPage from '../DashboardPage'
import { dashboardApi } from '../../api/dashboard'
import type {
  DashboardExpenseSummary,
  ProfitLossSummary,
  QuoteStatusSummary,
  SalesAndPaymentsSummary,
} from '../../types'

vi.mock('../../api/dashboard', () => ({
  dashboardApi: {
    salesAndPayments: vi.fn(),
    expenses: vi.fn(),
    profitLoss: vi.fn(),
    quotes: vi.fn(),
  },
}))

const mockedDashboardApi = vi.mocked(dashboardApi)

const MONTHS = [
  '2025-10',
  '2025-11',
  '2025-12',
  '2026-01',
  '2026-02',
  '2026-03',
  '2026-04',
  '2026-05',
  '2026-06',
  '2026-07',
  '2026-08',
  '2026-09',
]

function buildSalesAndPayments(): SalesAndPaymentsSummary {
  return {
    sales: MONTHS.map((month) => ({ month, amount: month === '2026-09' ? 500000 : 0 })),
    payments: MONTHS.map((month) => ({ month, amount: month === '2026-09' ? 300000 : 0 })),
  }
}

function buildExpenses(): DashboardExpenseSummary {
  return {
    monthly: MONTHS.map((month) => ({ month, amount: month === '2026-09' ? 200000 : 0 })),
    by_category: [{ account_category: '通信費', count: 2, total_amount: 200000 }],
  }
}

function buildProfitLoss(): ProfitLossSummary {
  return {
    monthly: MONTHS.map((month) => ({ month, amount: month === '2026-09' ? 300000 : 0 })),
  }
}

function buildQuotes(conversionRate: number | null = 0.5): QuoteStatusSummary {
  return {
    monthly: MONTHS.map((month) => ({
      month,
      count: month === '2026-09' ? 2 : 0,
      total_amount: month === '2026-09' ? 400000 : 0,
    })),
    conversion_rate: conversionRate,
  }
}

function renderDashboardPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DashboardPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('DashboardPage', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders all 4 sections and their totals when every API succeeds', async () => {
    mockedDashboardApi.salesAndPayments.mockResolvedValue(buildSalesAndPayments())
    mockedDashboardApi.expenses.mockResolvedValue(buildExpenses())
    mockedDashboardApi.profitLoss.mockResolvedValue(buildProfitLoss())
    mockedDashboardApi.quotes.mockResolvedValue(buildQuotes())

    renderDashboardPage()

    expect(screen.getByRole('heading', { name: '財務ダッシュボード' })).toBeInTheDocument()
    expect(screen.getByText('売上・入金状況')).toBeInTheDocument()
    expect(screen.getByText('経費')).toBeInTheDocument()
    expect(screen.getByText('損益(収支)')).toBeInTheDocument()
    expect(screen.getByText('見積状況')).toBeInTheDocument()

    await waitFor(() => expect(screen.getByText(/500,000円/)).toBeInTheDocument())
    expect(screen.getAllByText(/300,000円/).length).toBeGreaterThan(0)
    expect(screen.getByText('50%')).toBeInTheDocument()
    expect(screen.queryByText('情報を取得できませんでした')).not.toBeInTheDocument()
  })

  it('shows an error only in the failed section while other sections render normally', async () => {
    mockedDashboardApi.salesAndPayments.mockResolvedValue(buildSalesAndPayments())
    mockedDashboardApi.expenses.mockResolvedValue(buildExpenses())
    mockedDashboardApi.profitLoss.mockRejectedValue(new Error('network error'))
    mockedDashboardApi.quotes.mockResolvedValue(buildQuotes())

    renderDashboardPage()

    await waitFor(() => expect(screen.getByText('情報を取得できませんでした')).toBeInTheDocument())
    // 他区画は影響を受けず表示される
    expect(screen.getByText(/500,000円/)).toBeInTheDocument()
    expect(screen.getByText('50%')).toBeInTheDocument()
    expect(screen.getAllByText('情報を取得できませんでした')).toHaveLength(1)
  })

  it('displays "-" for the quote conversion rate when it cannot be computed (division by zero avoidance)', async () => {
    mockedDashboardApi.salesAndPayments.mockResolvedValue(buildSalesAndPayments())
    mockedDashboardApi.expenses.mockResolvedValue(buildExpenses())
    mockedDashboardApi.profitLoss.mockResolvedValue(buildProfitLoss())
    mockedDashboardApi.quotes.mockResolvedValue(buildQuotes(null))

    renderDashboardPage()

    await waitFor(() => expect(screen.getByText('-')).toBeInTheDocument())
  })
})
