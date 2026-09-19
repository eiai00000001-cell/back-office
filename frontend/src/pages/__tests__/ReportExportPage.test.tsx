import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import ReportExportPage from '../ReportExportPage'
import { reportsApi } from '../../api/reports'
import { defaultReportPeriod } from '../../utils/format'

vi.mock('../../api/reports', () => ({ reportsApi: { download: vi.fn() } }))

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ReportExportPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ReportExportPage (SC-18)', () => {
  const createObjectURL = vi.fn(() => 'blob:mock')
  const revokeObjectURL = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
    Object.assign(URL, { createObjectURL, revokeObjectURL })
    vi.mocked(reportsApi.download).mockResolvedValue({ blob: new Blob(['x']), filename: '請求書一覧_202510-202609.csv', recordCount: 3 })
  })
  afterEach(() => vi.restoreAllMocks())

  it('7種類の出力対象と期間の基準を表示し、初期期間は直近12ヶ月', () => {
    renderPage()
    for (const name of ['請求書一覧', '入金記録', '見積書一覧', '経費一覧', '月次損益集計レポート', '案件別サマリー', '会計ソフト連携用エクスポート(汎用CSV)']) {
      expect(screen.getByText(name)).toBeInTheDocument()
    }
    expect(screen.getAllByText(/期間の基準: 発行日/).length).toBeGreaterThan(0)
    expect(screen.getByText(/期間の基準: 案件の納期または紐付き請求書の発行日/)).toBeInTheDocument()
    const period = defaultReportPeriod()
    expect(screen.getByLabelText('開始年月')).toHaveValue(period.from)
    expect(screen.getByLabelText('終了年月')).toHaveValue(period.to)
  })

  it('種類が未選択なら出力せずメッセージを表示する', () => {
    renderPage()
    fireEvent.click(screen.getByRole('button', { name: '出力' }))
    expect(screen.getByText('出力する種類を選択してください')).toBeInTheDocument()
    expect(reportsApi.download).not.toHaveBeenCalled()
  })

  it('開始年月が終了年月より後なら出力せずメッセージを表示する', () => {
    renderPage()
    fireEvent.click(screen.getByRole('radio', { name: /請求書一覧/ }))
    fireEvent.change(screen.getByLabelText('開始年月'), { target: { value: '2026-10' } })
    fireEvent.change(screen.getByLabelText('終了年月'), { target: { value: '2026-09' } })
    fireEvent.click(screen.getByRole('button', { name: '出力' }))
    expect(screen.getByText('開始年月は終了年月以前を指定してください')).toBeInTheDocument()
    expect(reportsApi.download).not.toHaveBeenCalled()
  })

  it('出力形式は月次損益集計レポート選択時のみ表示する', () => {
    renderPage()
    fireEvent.click(screen.getByRole('radio', { name: /請求書一覧/ }))
    expect(screen.queryByLabelText('出力形式')).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('radio', { name: /月次損益集計レポート/ }))
    expect(screen.getByLabelText('出力形式')).toBeInTheDocument()
  })

  it('選択した種類・期間でダウンロードAPIを呼び、ファイルを保存する', async () => {
    const click = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    renderPage()
    fireEvent.click(screen.getByRole('radio', { name: /請求書一覧/ }))
    fireEvent.change(screen.getByLabelText('開始年月'), { target: { value: '2025-10' } })
    fireEvent.change(screen.getByLabelText('終了年月'), { target: { value: '2026-09' } })
    fireEvent.click(screen.getByRole('button', { name: '出力' }))
    await waitFor(() => expect(reportsApi.download).toHaveBeenCalledWith('invoices', '2025-10', '2026-09', 'csv'))
    await waitFor(() => expect(click).toHaveBeenCalled())
    expect(createObjectURL).toHaveBeenCalled()
    expect(screen.queryByText(/対象期間にデータがありませんでした/)).not.toBeInTheDocument()
  })

  it('月次損益集計レポートはPDFを選べる', async () => {
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    renderPage()
    fireEvent.click(screen.getByRole('radio', { name: /月次損益集計レポート/ }))
    fireEvent.mouseDown(screen.getByLabelText('出力形式'))
    fireEvent.click(await screen.findByRole('option', { name: 'PDF' }))
    fireEvent.click(screen.getByRole('button', { name: '出力' }))
    await waitFor(() => expect(reportsApi.download).toHaveBeenCalledWith('monthly-pl', expect.any(String), expect.any(String), 'pdf'))
  })

  it('件数0のときは項目名のみ出力した旨を表示する', async () => {
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    vi.mocked(reportsApi.download).mockResolvedValue({ blob: new Blob(['x']), filename: 'a.csv', recordCount: 0 })
    renderPage()
    fireEvent.click(screen.getByRole('radio', { name: /経費一覧/ }))
    fireEvent.click(screen.getByRole('button', { name: '出力' }))
    expect(await screen.findByText('対象期間にデータがありませんでした。項目名のみ出力しました')).toBeInTheDocument()
  })

  it.each([
    ['請求書一覧', '対象期間にデータがありませんでした。項目名のみ出力しました'],
    ['入金記録', '対象期間にデータがありませんでした。項目名のみ出力しました'],
    ['見積書一覧', '対象期間にデータがありませんでした。項目名のみ出力しました'],
    ['案件別サマリー', '対象期間にデータがありませんでした。項目名のみ出力しました'],
    ['会計ソフト連携用エクスポート', '対象期間にデータがありませんでした。項目名のみ出力しました'],
    ['月次損益集計レポート', '対象期間にデータがありませんでした。全月0円のレポートを出力しました'],
  ])('件数0の文言は種類別: %s', async (name, message) => {
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    vi.mocked(reportsApi.download).mockResolvedValue({ blob: new Blob(['x']), filename: 'a.csv', recordCount: 0 })
    renderPage()
    fireEvent.click(screen.getByRole('radio', { name: new RegExp(name) }))
    fireEvent.click(screen.getByRole('button', { name: '出力' }))
    expect(await screen.findByText(message)).toBeInTheDocument()
  })

  it('月次損益集計レポートのPDFでも全月0円の文言を表示する', async () => {
    vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
    vi.mocked(reportsApi.download).mockResolvedValue({ blob: new Blob(['x']), filename: 'a.pdf', recordCount: 0 })
    renderPage()
    fireEvent.click(screen.getByRole('radio', { name: /月次損益集計レポート/ }))
    fireEvent.mouseDown(screen.getByLabelText('出力形式'))
    fireEvent.click(await screen.findByRole('option', { name: 'PDF' }))
    fireEvent.click(screen.getByRole('button', { name: '出力' }))
    expect(await screen.findByText('対象期間にデータがありませんでした。全月0円のレポートを出力しました')).toBeInTheDocument()
  })

  it('年が2000〜2099の範囲外・120か月超は入力エラーにして出力しない', async () => {
    renderPage()
    fireEvent.click(screen.getByRole('radio', { name: /請求書一覧/ }))
    fireEvent.change(screen.getByLabelText('開始年月'), { target: { value: '1999-12' } })
    fireEvent.change(screen.getByLabelText('終了年月'), { target: { value: '2026-09' } })
    fireEvent.click(screen.getByRole('button', { name: '出力' }))
    expect(await screen.findByText('期間の年は2000〜2099の範囲で指定してください')).toBeInTheDocument()
    fireEvent.change(screen.getByLabelText('開始年月'), { target: { value: '2000-01' } })
    fireEvent.change(screen.getByLabelText('終了年月'), { target: { value: '2010-01' } })
    fireEvent.click(screen.getByRole('button', { name: '出力' }))
    expect(await screen.findByText('期間は最大120か月(10年)以内で指定してください')).toBeInTheDocument()
    expect(reportsApi.download).not.toHaveBeenCalled()
  })

  it('出力失敗時は「出力に失敗しました」を表示する', async () => {
    vi.mocked(reportsApi.download).mockRejectedValue(new Error('x'))
    renderPage()
    fireEvent.click(screen.getByRole('radio', { name: /経費一覧/ }))
    fireEvent.click(screen.getByRole('button', { name: '出力' }))
    expect(await screen.findByText('出力に失敗しました')).toBeInTheDocument()
  })

  it('CSVに関する注意(バックアップの代わりにならない)を表示する', () => {
    renderPage()
    expect(screen.getByText('CSV出力はバックアップの代わりにはなりません。')).toBeInTheDocument()
    expect(within(document.body).getByRole('link', { name: '← ホームへ' })).toHaveAttribute('href', '/')
  })

  it('年範囲違反と開始>終了が同時のときは、サーバーと同じく年範囲のメッセージを優先する', async () => {
    renderPage()
    fireEvent.click(screen.getByRole('radio', { name: /請求書一覧/ }))
    fireEvent.change(screen.getByLabelText('開始年月'), { target: { value: '2100-01' } })
    fireEvent.change(screen.getByLabelText('終了年月'), { target: { value: '2026-09' } })
    fireEvent.click(screen.getByRole('button', { name: '出力' }))
    expect(await screen.findByText('期間の年は2000〜2099の範囲で指定してください')).toBeInTheDocument()
    expect(screen.queryByText('開始年月は終了年月以前を指定してください')).not.toBeInTheDocument()
    expect(reportsApi.download).not.toHaveBeenCalled()
  })
})
