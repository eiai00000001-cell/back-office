import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import HomePage from '../HomePage'
import { homeApi } from '../../api/home'
import { notificationsApi } from '../../api/notifications'
import type { NotificationItem, NotificationSummary } from '../../types'

vi.mock('../../api/home', () => ({ homeApi: { summary: vi.fn() } }))
vi.mock('../../api/notifications', () => ({
  notificationsApi: { list: vi.fn(), summary: vi.fn(), acknowledge: vi.fn(), unacknowledge: vi.fn() },
}))

const item = (overrides: Partial<NotificationItem>): NotificationItem => ({
  source_type: 'INVOICE_DUE',
  source_id: 1,
  title: '請求書 2026-0004(株式会社サンプル商事)の支払期限',
  due_date: '2026-08-31',
  state: 'OVERDUE',
  days_diff: -19,
  link: '/invoices/1',
  category: null,
  acknowledged: false,
  ...overrides,
})

const summary = (overrides: Partial<NotificationSummary> = {}): NotificationSummary => ({
  unacknowledged_count: 2,
  overdue_count: 1,
  items: [
    item({}),
    item({ source_type: 'PROJECT_DUE', source_id: 5, title: '案件「店舗パンフレット制作」の納期', state: 'UPCOMING', link: '/projects/5', due_date: '2026-09-24' }),
  ],
  errors: [],
  ...overrides,
})

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <HomePage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('HomePage 通知エリア(F-09)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(homeApi.summary).mockResolvedValue({ unpaid_count: 3, overdue_count: 1 })
    vi.mocked(notificationsApi.summary).mockResolvedValue(summary())
  })

  it('未確認件数・超過件数と上位の通知(種類・期限日・超過/接近バッジ)を表示する', async () => {
    renderPage()
    const area = await screen.findByTestId('notice-area')
    await within(area).findByText('請求書 2026-0004(株式会社サンプル商事)の支払期限')
    expect(within(area).getByTestId('notice-head')).toHaveTextContent('未確認 2 件(うち期限超過 1 件)')
    expect(within(area).getByText('請求書の支払期限')).toBeInTheDocument()
    expect(within(area).getByText('案件の納期')).toBeInTheDocument()
    expect(within(area).getByText('超過')).toBeInTheDocument()
    expect(within(area).getByText('接近')).toBeInTheDocument()
    expect(within(area).getByText('2026-08-31')).toBeInTheDocument()
    expect(within(area).getByRole('link', { name: '請求書 2026-0004(株式会社サンプル商事)の支払期限' })).toHaveAttribute('href', '/invoices/1')
    expect(within(area).getByRole('link', { name: 'すべての通知を見る →' })).toHaveAttribute('href', '/notifications')
  })

  it('「確認済み」ボタンでAPIを呼び、通知を再取得する', async () => {
    vi.mocked(notificationsApi.acknowledge).mockResolvedValue()
    renderPage()
    const area = await screen.findByTestId('notice-area')
    await within(area).findByText('請求書 2026-0004(株式会社サンプル商事)の支払期限')
    fireEvent.click(within(area).getAllByRole('button', { name: '確認済み' })[0])
    await waitFor(() =>
      expect(notificationsApi.acknowledge).toHaveBeenCalledWith({ source_type: 'INVOICE_DUE', source_id: 1 })
    )
    await waitFor(() => expect(notificationsApi.summary).toHaveBeenCalledTimes(2))
  })

  it('解消済み(404)の場合はメッセージを表示して再取得する', async () => {
    vi.mocked(notificationsApi.acknowledge).mockRejectedValue({
      response: { status: 404, data: { detail: '対象の通知は既に解消されています' } },
    })
    renderPage()
    const area = await screen.findByTestId('notice-area')
    await within(area).findByText('請求書 2026-0004(株式会社サンプル商事)の支払期限')
    fireEvent.click(within(area).getAllByRole('button', { name: '確認済み' })[0])
    expect(await within(area).findByText('対象の通知は既に解消されています')).toBeInTheDocument()
    await waitFor(() => expect(notificationsApi.summary).toHaveBeenCalledTimes(2))
  })

  it('通知APIが失敗しても通知エリアのみエラー表示で、既存サマリー・カードは表示される', async () => {
    vi.mocked(notificationsApi.summary).mockRejectedValue(new Error('x'))
    renderPage()
    expect(await screen.findByText('通知を取得できませんでした。')).toBeInTheDocument()
    expect(await screen.findByText('3')).toBeInTheDocument() // 未入金件数
    expect(screen.getByText('財務ダッシュボード')).toBeInTheDocument()
  })

  it('既存サマリーが失敗しても通知エリアは表示される', async () => {
    vi.mocked(homeApi.summary).mockRejectedValue(new Error('x'))
    renderPage()
    expect(await screen.findByText('サマリー情報を取得できませんでした。')).toBeInTheDocument()
    expect(await screen.findByText('請求書 2026-0004(株式会社サンプル商事)の支払期限')).toBeInTheDocument()
  })

  it('一部の種類の取得失敗を通知エリアに表示する', async () => {
    vi.mocked(notificationsApi.summary).mockResolvedValue(summary({ errors: ['QUOTE_EXPIRY'] }))
    renderPage()
    expect(await screen.findByText('一部の通知を取得できませんでした(見積書の有効期限)')).toBeInTheDocument()
  })

  it('未確認の通知が0件のときは通知なしを表示する', async () => {
    vi.mocked(notificationsApi.summary).mockResolvedValue(summary({ unacknowledged_count: 0, overdue_count: 0, items: [] }))
    renderPage()
    expect(await screen.findByText('未確認の通知はありません。')).toBeInTheDocument()
  })

  it('導線カードに「通知・期限」「レポート出力」がある', async () => {
    renderPage()
    expect(await screen.findByRole('link', { name: /通知・期限/ })).toHaveAttribute('href', '/notifications')
    expect(screen.getByRole('link', { name: /レポート出力/ })).toHaveAttribute('href', '/reports')
    expect(screen.getByRole('link', { name: /案件管理/ })).toHaveAttribute('href', '/projects/kanban')
  })
})
