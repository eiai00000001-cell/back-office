import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ExpenseFormPage from '../ExpenseFormPage'
import { expensesApi } from '../../api/expenses'
import { projectsApi } from '../../api/projects'

vi.mock('../../api/expenses', () => ({
  expensesApi: {
    list: vi.fn(),
    get: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    remove: vi.fn(),
    uploadAttachment: vi.fn(),
    attachmentUrl: (id: number) => `/api/expenses/${id}/attachment`,
    summary: vi.fn(),
    linkProject: vi.fn(),
  },
}))

vi.mock('../../api/projects', () => ({
  projectsApi: { list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), changeStatus: vi.fn(), remove: vi.fn() },
}))

const mockedExpensesApi = vi.mocked(expensesApi)
const mockedProjectsApi = vi.mocked(projectsApi)

function renderExpenseFormPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/expenses/new']}>
        <Routes>
          <Route path="/expenses/:id" element={<ExpenseFormPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

function buildFile(name: string, sizeBytes: number, type: string): File {
  const file = new File([new Uint8Array(sizeBytes)], name, { type })
  return file
}

describe('ExpenseFormPage 添付ファイル検証', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockedProjectsApi.list.mockResolvedValue([])
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('許可されていない拡張子のファイルを選択するとエラーメッセージを表示する', async () => {
    renderExpenseFormPage()

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const disallowedFile = buildFile('receipt.txt', 1024, 'text/plain')

    fireEvent.change(fileInput, { target: { files: [disallowedFile] } })

    expect(
      await screen.findByText('対応していないファイル形式、またはサイズが上限(10MB)を超えています')
    ).toBeInTheDocument()
  })

  it('サイズが上限(10MB)を超えるファイルを選択するとエラーメッセージを表示する', async () => {
    renderExpenseFormPage()

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const oversizedFile = buildFile('receipt.jpg', 10 * 1024 * 1024 + 1, 'image/jpeg')

    fireEvent.change(fileInput, { target: { files: [oversizedFile] } })

    expect(
      await screen.findByText('対応していないファイル形式、またはサイズが上限(10MB)を超えています')
    ).toBeInTheDocument()
  })

  it('許可された拡張子・サイズのファイルは受け付けてファイル名を表示する', async () => {
    renderExpenseFormPage()

    const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement
    const validFile = buildFile('receipt.png', 1024, 'image/png')

    fireEvent.change(fileInput, { target: { files: [validFile] } })

    expect(await screen.findByText('receipt.png')).toBeInTheDocument()
    expect(
      screen.queryByText('対応していないファイル形式、またはサイズが上限(10MB)を超えています')
    ).not.toBeInTheDocument()
  })

  it('金額が未入力の場合は保存ボタンが無効化される', async () => {
    renderExpenseFormPage()

    await screen.findByLabelText(/発生日/)
    expect(screen.getByRole('button', { name: '保存' })).toBeDisabled()
  })

  it('必須項目を入力すると保存ボタンが有効化され、保存処理が呼ばれる', async () => {
    const savedExpense = {
      id: 1,
      expense_date: '2026-09-12',
      account_category: '消耗品費',
      amount: 3300,
      tax_category: 'STANDARD_10' as const,
      payee: null,
      payment_method: null,
      memo: null,
      attachment_path: null,
      attachment_original_name: null,
      project_id: null,
      project_name: null,
    }
    mockedExpensesApi.create.mockResolvedValue(savedExpense)
    // 保存成功後、/expenses/1へnavigateしてisNewがfalseになり expense 取得クエリが発火するため
    // 併せてモックしておく(テスト実行時の未処理な警告を避ける)。
    mockedExpensesApi.get.mockResolvedValue(savedExpense)

    renderExpenseFormPage()

    fireEvent.change(screen.getByLabelText(/^金額/), { target: { value: '3300' } })

    const saveButton = screen.getByRole('button', { name: '保存' })
    await waitFor(() => expect(saveButton).not.toBeDisabled())

    fireEvent.click(saveButton)

    await waitFor(() => expect(mockedExpensesApi.create).toHaveBeenCalledWith(expect.objectContaining({ project_id: null })))
  })
})
