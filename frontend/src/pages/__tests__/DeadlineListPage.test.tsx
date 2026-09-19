import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import DeadlineListPage from '../DeadlineListPage'
import { deadlinesApi } from '../../api/deadlines'
import type { Deadline } from '../../types'

vi.mock('../../api/deadlines', () => ({
  deadlinesApi: { list: vi.fn(), create: vi.fn(), update: vi.fn(), remove: vi.fn() },
}))

const dl = (overrides: Partial<Deadline>): Deadline => ({
  id: 1,
  name: '契約更新(サンプル保守契約)',
  due_date: '2026-09-30',
  category: 'CONTRACT_RENEWAL',
  memo: '更新の連絡は9月中',
  is_recurring: false,
  due_state: 'UPCOMING',
  ...overrides,
})

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <DeadlineListPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('DeadlineListPage (SC-17)', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(deadlinesApi.list).mockResolvedValue([
      dl({}),
      dl({ id: 2, name: '確定申告(サンプル)', due_date: '2027-03-15', category: 'TAX_FILING', memo: null, is_recurring: true, due_state: null }),
    ])
  })

  it('期限の一覧(名称・期限日・種別・毎年繰り返し・メモ・状態)を表示する', async () => {
    renderPage()
    await screen.findByText('契約更新(サンプル保守契約)')
    const rows = screen.getAllByRole('row')
    expect(within(rows[1]).getByText('2026-09-30')).toBeInTheDocument()
    expect(within(rows[1]).getByText('接近')).toBeInTheDocument()
    expect(within(rows[1]).getByText('契約更新')).toBeInTheDocument()
    expect(within(rows[1]).getByText('なし')).toBeInTheDocument()
    expect(within(rows[1]).getByText('更新の連絡は9月中')).toBeInTheDocument()
    expect(within(rows[2]).getByText('毎年')).toBeInTheDocument()
    expect(within(rows[2]).getByText('確定申告')).toBeInTheDocument()
    expect(screen.getByRole('link', { name: '← 通知一覧へ' })).toHaveAttribute('href', '/notifications')
  })

  it('新規登録: 名称・期限日が未入力なら保存せず、入力メッセージを表示する', async () => {
    renderPage()
    await screen.findByText('契約更新(サンプル保守契約)')
    fireEvent.click(screen.getByRole('button', { name: '新規登録' }))
    const dialog = await screen.findByRole('dialog')
    fireEvent.click(within(dialog).getByRole('button', { name: '保存' }))
    expect(await within(dialog).findByText('名称を入力してください')).toBeInTheDocument()
    expect(within(dialog).getByText('期限日を入力してください')).toBeInTheDocument()
    expect(deadlinesApi.create).not.toHaveBeenCalled()
  })

  it('新規登録: 入力内容を送信し、一覧を再取得する', async () => {
    vi.mocked(deadlinesApi.create).mockResolvedValue(dl({ id: 9 }))
    renderPage()
    await screen.findByText('契約更新(サンプル保守契約)')
    fireEvent.click(screen.getByRole('button', { name: '新規登録' }))
    const dialog = await screen.findByRole('dialog')
    fireEvent.change(within(dialog).getByLabelText(/名称/), { target: { value: '  更新A ' } })
    fireEvent.change(within(dialog).getByLabelText(/期限日/), { target: { value: '2026-12-01' } })
    fireEvent.click(within(dialog).getByLabelText('毎年繰り返す'))
    fireEvent.change(within(dialog).getByLabelText(/メモ/), { target: { value: 'm' } })
    fireEvent.click(within(dialog).getByRole('button', { name: '保存' }))
    await waitFor(() =>
      expect(deadlinesApi.create).toHaveBeenCalledWith({
        name: '更新A',
        due_date: '2026-12-01',
        category: 'OTHER',
        memo: 'm',
        is_recurring: true,
      })
    )
    await waitFor(() => expect(deadlinesApi.list).toHaveBeenCalledTimes(2))
  })

  it('編集: 既存値が入り、更新APIが呼ばれる', async () => {
    vi.mocked(deadlinesApi.update).mockResolvedValue(dl({}))
    renderPage()
    await screen.findByText('契約更新(サンプル保守契約)')
    fireEvent.click(screen.getAllByRole('button', { name: '編集' })[0])
    const dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByLabelText(/名称/)).toHaveValue('契約更新(サンプル保守契約)')
    expect(within(dialog).getByLabelText(/期限日/)).toHaveValue('2026-09-30')
    fireEvent.change(within(dialog).getByLabelText(/名称/), { target: { value: '更新後' } })
    fireEvent.click(within(dialog).getByRole('button', { name: '保存' }))
    await waitFor(() =>
      expect(deadlinesApi.update).toHaveBeenCalledWith(1, expect.objectContaining({ name: '更新後', due_date: '2026-09-30', category: 'CONTRACT_RENEWAL' }))
    )
  })

  it('サーバーエラーは保存ダイアログ内に表示する', async () => {
    vi.mocked(deadlinesApi.create).mockRejectedValue({ response: { data: { detail: '期限日は日付(YYYY-MM-DD)で入力してください' } } })
    renderPage()
    await screen.findByText('契約更新(サンプル保守契約)')
    fireEvent.click(screen.getByRole('button', { name: '新規登録' }))
    const dialog = await screen.findByRole('dialog')
    fireEvent.change(within(dialog).getByLabelText(/名称/), { target: { value: 'A' } })
    fireEvent.change(within(dialog).getByLabelText(/期限日/), { target: { value: '2026-12-01' } })
    fireEvent.click(within(dialog).getByRole('button', { name: '保存' }))
    expect(await within(dialog).findByText('期限日は日付(YYYY-MM-DD)で入力してください')).toBeInTheDocument()
  })

  it('削除: 確認ダイアログで承認したときのみ削除する', async () => {
    vi.mocked(deadlinesApi.remove).mockResolvedValue()
    renderPage()
    await screen.findByText('契約更新(サンプル保守契約)')
    fireEvent.click(screen.getAllByRole('button', { name: '削除' })[0])
    let dialog = await screen.findByRole('dialog')
    fireEvent.click(within(dialog).getByRole('button', { name: 'キャンセル' }))
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument())
    expect(deadlinesApi.remove).not.toHaveBeenCalled()

    fireEvent.click(screen.getAllByRole('button', { name: '削除' })[0])
    dialog = await screen.findByRole('dialog')
    expect(within(dialog).getByText(/契約更新\(サンプル保守契約\)/)).toBeInTheDocument()
    fireEvent.click(within(dialog).getByRole('button', { name: '削除する' }))
    await waitFor(() => expect(deadlinesApi.remove).toHaveBeenCalledWith(1))
  })

  it('一覧取得失敗時はエラー表示', async () => {
    vi.mocked(deadlinesApi.list).mockRejectedValue(new Error('x'))
    renderPage()
    expect(await screen.findByText('期限を取得できませんでした。')).toBeInTheDocument()
  })
})
