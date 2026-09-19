import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProjectDetailPage from '../ProjectDetailPage'
import { clientsApi } from '../../api/clients'
import { invoicesApi } from '../../api/invoices'
import { quotesApi } from '../../api/quotes'
import { projectsApi } from '../../api/projects'
import type { InvoiceListItem, ProjectDetail } from '../../types'

vi.mock('../../api/clients', () => ({ clientsApi: { list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn() } }))
vi.mock('../../api/invoices', () => ({ invoicesApi: { list: vi.fn(), linkProject: vi.fn() } }))
vi.mock('../../api/quotes', () => ({ quotesApi: { list: vi.fn(), linkProject: vi.fn() } }))
vi.mock('../../api/projects', () => ({
  projectsApi: { list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), changeStatus: vi.fn(), remove: vi.fn() },
}))

const mockedProjectsApi = vi.mocked(projectsApi)
const mockedInvoicesApi = vi.mocked(invoicesApi)

const detail: ProjectDetail = {
  id: 7,
  name: '自社サイトリニューアル',
  client_id: null,
  client_name: null,
  status: 'IN_PROGRESS',
  due_date: '2026-12-01',
  description: 'メモ',
  quote_count: 0,
  invoice_count: 1,
  due_state: null,
  quotes: [],
  invoices: [
    { id: 30, invoice_number: '2026-0030', issue_date: null, due_date: null, total_amount: 110000, payment_status: 'UNPAID' },
  ],
  summary: { quote_count: 0, quote_total: 0, invoice_count: 1, invoice_total: 110000, paid_total: 0, unpaid_total: 110000 },
}

const invoiceRow = (o: Partial<InvoiceListItem>): InvoiceListItem => ({
  id: 1,
  invoice_number: '2026-0001',
  client_id: 5,
  client_name: '株式会社サンプル商事',
  issue_date: '2026-08-01',
  due_date: '2026-08-31',
  total_amount: 55000,
  paid_amount: 0,
  project_id: null,
  project_name: null,
  payment_status: 'UNPAID',
  is_overdue: false,
  ...o,
})

function renderPage(path = '/projects/7') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/projects/:id" element={<ProjectDetailPage />} />
          <Route path="/projects" element={<div>案件一覧ページ</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ProjectDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(clientsApi.list).mockResolvedValue([])
    mockedProjectsApi.get.mockResolvedValue(detail)
    mockedProjectsApi.list.mockResolvedValue([])
    vi.mocked(quotesApi.list).mockResolvedValue([])
  })

  it('案件情報・集計サマリー・紐付き請求書を表示する', async () => {
    renderPage()
    expect(await screen.findByDisplayValue('自社サイトリニューアル')).toBeInTheDocument()
    expect(screen.getByText('請求書(1件)')).toBeInTheDocument()
    expect(screen.getByText('2026-0030')).toBeInTheDocument()
  })

  it('案件名が空白のみの場合は保存せずエラーを表示する', async () => {
    renderPage()
    const nameInput = await screen.findByDisplayValue('自社サイトリニューアル')
    fireEvent.change(nameInput, { target: { value: '   ' } })
    fireEvent.click(screen.getByRole('button', { name: '保存' }))
    expect(await screen.findByText('案件名を入力してください')).toBeInTheDocument()
    expect(mockedProjectsApi.update).not.toHaveBeenCalled()
  })

  it('新規作成時は削除ボタンを表示しない', async () => {
    renderPage('/projects/new')
    await screen.findByLabelText(/案件名/)
    expect(screen.queryByRole('button', { name: '削除' })).not.toBeInTheDocument()
  })

  it('紐付けを解除すると project_id: null で専用APIを呼ぶ', async () => {
    mockedInvoicesApi.linkProject.mockResolvedValue({} as never)
    renderPage()
    await screen.findByText('2026-0030')
    fireEvent.click(screen.getByRole('button', { name: '紐付けを解除' }))
    await waitFor(() => expect(mockedInvoicesApi.linkProject).toHaveBeenCalledWith(30, null))
  })

  it('別案件に紐付いた請求書を選ぶと移動の確認を表示し、確定すると当案件へ紐付ける', async () => {
    mockedProjectsApi.list.mockResolvedValue([])
    mockedInvoicesApi.list.mockResolvedValue([
      invoiceRow({ id: 1, invoice_number: '2026-0001', project_id: 9, project_name: 'ロゴデザイン制作' }),
      invoiceRow({ id: 2, invoice_number: '2026-0002' }),
      invoiceRow({ id: 30, invoice_number: '2026-0030', project_id: 7, project_name: '自社サイトリニューアル' }),
    ])
    mockedInvoicesApi.linkProject.mockResolvedValue({} as never)
    renderPage()
    await screen.findByText('2026-0030')
    fireEvent.click(screen.getByRole('button', { name: '請求書を紐付ける' }))
    const dialog = await screen.findByRole('dialog')
    // 既に当案件へ紐付いている請求書は候補に出ない
    expect(within(dialog).queryByText('2026-0030')).not.toBeInTheDocument()
    fireEvent.click(await within(dialog).findByLabelText('2026-0001を選択'))
    expect(within(dialog).getByText('案件「ロゴデザイン制作」から移動します。よろしいですか?')).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: '紐付ける' }))
    await waitFor(() => expect(mockedInvoicesApi.linkProject).toHaveBeenCalledWith(1, 7))
  })

  it('削除は確認メッセージを表示し、承認時のみ削除する', async () => {
    mockedProjectsApi.remove.mockResolvedValue(undefined)
    renderPage()
    await screen.findByDisplayValue('自社サイトリニューアル')
    fireEvent.click(screen.getByRole('button', { name: '削除' }))
    const dialog = await screen.findByRole('dialog')
    expect(
      within(dialog).getByText('この案件を削除します。紐付いている見積書・請求書・経費は削除されず、「案件なし」に戻ります。')
    ).toBeInTheDocument()
    expect(mockedProjectsApi.remove).not.toHaveBeenCalled()
    fireEvent.click(within(dialog).getByRole('button', { name: '削除する' }))
    await waitFor(() => expect(mockedProjectsApi.remove).toHaveBeenCalledWith(7))
  })
})
