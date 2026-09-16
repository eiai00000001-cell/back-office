import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import QuoteDetailPage from '../QuoteDetailPage'
import { clientsApi } from '../../api/clients'
import { quotesApi } from '../../api/quotes'
import type { Client, Quote } from '../../types'

vi.mock('../../api/clients', () => ({
  clientsApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
  },
}))

vi.mock('../../api/quotes', () => ({
  quotesApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    pdfUrl: (id: number) => `/api/quotes/${id}/pdf`,
    convertToInvoice: vi.fn(),
  },
}))

const mockedClientsApi = vi.mocked(clientsApi)
const mockedQuotesApi = vi.mocked(quotesApi)

const sampleClients: Client[] = [
  { id: 5, name: '株式会社サンプル商事', postal_code: null, address: null, contact_person: null, contact_info: null },
]

const buildQuote = (overrides: Partial<Quote> = {}): Quote => ({
  id: 1,
  quote_number: '2026-0001',
  client_id: 5,
  client_name: '株式会社サンプル商事',
  issue_date: '2026-07-25',
  expiry_date: '2026-08-25',
  status: 'DRAFT',
  items: [
    { id: 10, item_name: 'Webサイト制作作業', quantity: 1, unit_price: 300000, tax_category: 'STANDARD_10', amount: 300000, sort_order: 0 },
  ],
  subtotal_amount: 300000,
  tax_amount: 30000,
  total_amount: 330000,
  remarks: null,
  converted_invoice_id: null,
  converted_invoice_number: null,
  ...overrides,
})

function renderQuoteDetailPage(initialPath = '/quotes/1') {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path="/quotes/:id" element={<QuoteDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('QuoteDetailPage', () => {
  beforeEach(() => {
    mockedClientsApi.list.mockResolvedValue(sampleClients)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('取引先選択欄に「新規登録」リンクがあり、取引先マスタ画面(returnTo付き)へ遷移する', async () => {
    mockedQuotesApi.get.mockResolvedValue(buildQuote())

    renderQuoteDetailPage('/quotes/1')

    await screen.findByDisplayValue('Webサイト制作作業')

    const newClientLink = screen.getByRole('link', { name: '新規登録' })
    expect(newClientLink).toHaveAttribute('href', `/clients?returnTo=${encodeURIComponent('/quotes/1')}`)
  })

  it('取引先マスタ画面から selectedClientId 付きで戻ると、当該取引先が選択済みになる', async () => {
    mockedQuotesApi.get.mockResolvedValue(buildQuote())
    mockedClientsApi.list.mockResolvedValue([
      ...sampleClients,
      { id: 9, name: '新規取引先株式会社', postal_code: null, address: null, contact_person: null, contact_info: null },
    ])

    renderQuoteDetailPage('/quotes/1?selectedClientId=9')

    await waitFor(() => {
      expect(screen.getByLabelText('取引先')).toHaveValue('新規取引先株式会社')
    })
  })
})
