import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import NotificationListPage from '../NotificationListPage'
import { notificationsApi } from '../../api/notifications'
import type { NotificationItem, NotificationList } from '../../types'

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

const list = (overrides: Partial<NotificationList> = {}): NotificationList => ({
  items: [
    item({}),
    item({ source_type: 'DEADLINE', source_id: 2, title: '契約更新(サンプル)(契約更新)', state: 'UPCOMING', link: '/deadlines', category: 'CONTRACT_RENEWAL', due_date: '2026-09-30' }),
  ],
  errors: [],
  ...overrides,
})

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <NotificationListPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('NotificationListPage (SC-16)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(notificationsApi.list).mockResolvedValue(list())
  })

  it('既定は確認済みを含めず取得し、種類・期限日・状態バッジ・ボタンを表示する', async () => {
    renderPage()
    await screen.findByText('請求書 2026-0004(株式会社サンプル商事)の支払期限')
    expect(notificationsApi.list).toHaveBeenCalledWith(false)
    const rows = screen.getAllByRole('row')
    expect(within(rows[1]).getByText('請求書の支払期限')).toBeInTheDocument()
    expect(within(rows[1]).getByText('超過')).toBeInTheDocument()
    expect(within(rows[2]).getByText('登録した期限')).toBeInTheDocument()
    expect(within(rows[2]).getByText('接近')).toBeInTheDocument()
    expect(within(rows[1]).getByRole('button', { name: '確認済み' })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '期限を登録・編集' })).toHaveAttribute('href', '/deadlines')
    expect(screen.getByRole('link', { name: '請求書 2026-0004(株式会社サンプル商事)の支払期限' })).toHaveAttribute('href', '/invoices/1')
  })

  it('「確認済みも表示」をオンにするとinclude_acknowledged=trueで再取得し、確認済み行には「未確認に戻す」を出す', async () => {
    vi.mocked(notificationsApi.list).mockImplementation(async (include) =>
      include ? list({ items: [item({ acknowledged: true })] }) : list()
    )
    renderPage()
    await screen.findByText('契約更新(サンプル)(契約更新)')
    fireEvent.click(screen.getByRole('checkbox', { name: '確認済みも表示' }))
    await waitFor(() => expect(notificationsApi.list).toHaveBeenCalledWith(true))
    const row = (await screen.findByRole('button', { name: '未確認に戻す' })).closest('tr') as HTMLElement
    expect(within(row).getByText('確認済み')).toBeInTheDocument()
  })

  it('「確認済み」で確認APIを呼び再取得する', async () => {
    vi.mocked(notificationsApi.acknowledge).mockResolvedValue()
    renderPage()
    await screen.findByText('契約更新(サンプル)(契約更新)')
    fireEvent.click(screen.getAllByRole('button', { name: '確認済み' })[1])
    await waitFor(() => expect(notificationsApi.acknowledge).toHaveBeenCalledWith({ source_type: 'DEADLINE', source_id: 2 }))
    await waitFor(() => expect(notificationsApi.list).toHaveBeenCalledTimes(2))
  })

  it('「未確認に戻す」で取消APIを呼ぶ', async () => {
    vi.mocked(notificationsApi.list).mockResolvedValue(list({ items: [item({ acknowledged: true })] }))
    vi.mocked(notificationsApi.unacknowledge).mockResolvedValue()
    renderPage()
    fireEvent.click(await screen.findByRole('checkbox', { name: '確認済みも表示' }))
    fireEvent.click(await screen.findByRole('button', { name: '未確認に戻す' }))
    await waitFor(() => expect(notificationsApi.unacknowledge).toHaveBeenCalledWith({ source_type: 'INVOICE_DUE', source_id: 1 }))
  })

  it('解消済み(404)ではメッセージを表示して再取得する', async () => {
    vi.mocked(notificationsApi.acknowledge).mockRejectedValue({
      response: { status: 404, data: { detail: '対象の通知は既に解消されています' } },
    })
    renderPage()
    await screen.findByText('契約更新(サンプル)(契約更新)')
    fireEvent.click(screen.getAllByRole('button', { name: '確認済み' })[0])
    expect(await screen.findByText('対象の通知は既に解消されています')).toBeInTheDocument()
    await waitFor(() => expect(notificationsApi.list).toHaveBeenCalledTimes(2))
  })

  it('errorsがある場合は種類名を挙げて表示し、取得できた通知は表示する', async () => {
    vi.mocked(notificationsApi.list).mockResolvedValue(list({ errors: ['INVOICE_DUE', 'QUOTE_EXPIRY'] }))
    renderPage()
    expect(await screen.findByText('一部の通知を取得できませんでした(請求書の支払期限、見積書の有効期限)')).toBeInTheDocument()
    expect(screen.getByText('契約更新(サンプル)(契約更新)')).toBeInTheDocument()
  })

  it('通知が0件のときは空表示', async () => {
    vi.mocked(notificationsApi.list).mockResolvedValue(list({ items: [] }))
    renderPage()
    expect(await screen.findByText('表示する通知はありません。')).toBeInTheDocument()
  })

  it('取得失敗時はエラー表示', async () => {
    vi.mocked(notificationsApi.list).mockRejectedValue(new Error('x'))
    renderPage()
    expect(await screen.findByText('通知を取得できませんでした。')).toBeInTheDocument()
  })
})
