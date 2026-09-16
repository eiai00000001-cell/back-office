import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import InvoiceDetailPage from '../InvoiceDetailPage'
import { clientsApi } from '../../api/clients'
import { invoicesApi } from '../../api/invoices'
import type { Client, Invoice } from '../../types'

vi.mock('../../api/clients', () => ({
  clientsApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
  },
}))

vi.mock('../../api/invoices', () => ({
  invoicesApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    pdfUrl: (id: number) => `/api/invoices/${id}/pdf`,
    listPayments: vi.fn(),
    addPayment: vi.fn(),
    removePayment: vi.fn(),
  },
}))

const mockedClientsApi = vi.mocked(clientsApi)
const mockedInvoicesApi = vi.mocked(invoicesApi)

const sampleClients: Client[] = [
  { id: 5, name: '株式会社サンプル商事', postal_code: null, address: null, contact_person: null, contact_info: null },
]

const buildInvoice = (overrides: Partial<Invoice> = {}): Invoice => ({
  id: 1,
  invoice_number: '2026-0001',
  client_id: 5,
  client_name: '株式会社サンプル商事',
  issue_date: '2026-08-01',
  due_date: '2026-08-31',
  source_quote_id: null,
  items: [
    { id: 10, item_name: 'Webサイト制作作業', quantity: 1, unit_price: 300000, tax_category: 'STANDARD_10', amount: 300000, sort_order: 0 },
  ],
  subtotal_amount: 300000,
  tax_amount: 30000,
  total_amount: 330000,
  remarks: null,
  payments: [],
  payment_status: 'UNPAID',
  is_overdue: false,
  ...overrides,
})

function renderInvoiceDetailPage(initialPath = '/invoices/1') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/invoices/:id" element={<InvoiceDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('InvoiceDetailPage', () => {
  beforeEach(() => {
    mockedClientsApi.list.mockResolvedValue(sampleClients)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('保存ボタンをクリックすると invoicesApi.update が呼ばれる', async () => {
    mockedInvoicesApi.get.mockResolvedValue(buildInvoice())
    mockedInvoicesApi.update.mockResolvedValue(buildInvoice())

    renderInvoiceDetailPage()

    await screen.findByDisplayValue('Webサイト制作作業')

    fireEvent.click(screen.getByRole('button', { name: '保存' }))

    await waitFor(() => {
      expect(mockedInvoicesApi.update).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          client_id: 5,
          items: expect.arrayContaining([expect.objectContaining({ item_name: 'Webサイト制作作業' })]),
        })
      )
    })
  })

  it('品目明細を全て削除すると保存ボタンが無効化される', async () => {
    mockedInvoicesApi.get.mockResolvedValue(buildInvoice())

    renderInvoiceDetailPage()

    await screen.findByDisplayValue('Webサイト制作作業')
    fireEvent.click(screen.getByRole('button', { name: '削除' }))

    expect(screen.getByRole('button', { name: '保存' })).toBeDisabled()
  })

  it('入金額が請求金額を超過する場合、確認ダイアログを表示し確認後に強制登録する', async () => {
    mockedInvoicesApi.get.mockResolvedValue(buildInvoice())
    mockedInvoicesApi.addPayment
      .mockRejectedValueOnce({
        response: { data: { detail: '入金額合計が請求金額を超過しています' } },
      })
      .mockResolvedValueOnce({ id: 100, invoice_id: 1, payment_date: '2026-08-15', amount: 400000, remarks: null })

    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)

    renderInvoiceDetailPage()

    await screen.findByDisplayValue('Webサイト制作作業')

    fireEvent.change(screen.getByLabelText('入金額'), { target: { value: '400000' } })
    fireEvent.click(screen.getByRole('button', { name: '追加' }))

    await waitFor(() => expect(confirmSpy).toHaveBeenCalled())
    expect(confirmSpy.mock.calls[0][0]).toContain('超過')

    await waitFor(() => expect(mockedInvoicesApi.addPayment).toHaveBeenCalledTimes(2))
    expect(mockedInvoicesApi.addPayment).toHaveBeenLastCalledWith(
      1,
      expect.objectContaining({ amount: 400000, force: true })
    )
  })

  it('取引先選択欄に「新規登録」リンクがあり、取引先マスタ画面(returnTo付き)へ遷移する', async () => {
    mockedInvoicesApi.get.mockResolvedValue(buildInvoice())

    renderInvoiceDetailPage('/invoices/1')

    await screen.findByDisplayValue('Webサイト制作作業')

    const newClientLink = screen.getByRole('link', { name: '新規登録' })
    expect(newClientLink).toHaveAttribute('href', `/clients?returnTo=${encodeURIComponent('/invoices/1')}`)
  })

  it('取引先マスタ画面から selectedClientId 付きで戻ると、当該取引先が選択済みになる', async () => {
    mockedInvoicesApi.get.mockResolvedValue(buildInvoice())
    mockedClientsApi.list.mockResolvedValue([
      ...sampleClients,
      { id: 9, name: '新規取引先株式会社', postal_code: null, address: null, contact_person: null, contact_info: null },
    ])

    renderInvoiceDetailPage('/invoices/1?selectedClientId=9')

    await waitFor(() => {
      expect(screen.getByLabelText('取引先')).toHaveValue('新規取引先株式会社')
    })
  })
})
