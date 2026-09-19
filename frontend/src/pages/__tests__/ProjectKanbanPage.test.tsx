import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import ProjectKanbanPage from '../ProjectKanbanPage'
import { clientsApi } from '../../api/clients'
import { projectsApi } from '../../api/projects'
import type { ProjectListItem } from '../../types'

vi.mock('../../api/clients', () => ({ clientsApi: { list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn() } }))
vi.mock('../../api/projects', () => ({
  projectsApi: { list: vi.fn(), get: vi.fn(), create: vi.fn(), update: vi.fn(), changeStatus: vi.fn(), remove: vi.fn() },
}))

const mockedProjectsApi = vi.mocked(projectsApi)

const build = (overrides: Partial<ProjectListItem>): ProjectListItem => ({
  id: 1,
  name: '案件A',
  client_id: null,
  client_name: null,
  status: 'NOT_STARTED',
  due_date: null,
  description: null,
  quote_count: 0,
  invoice_count: 0,
  due_state: null,
  ...overrides,
})

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <ProjectKanbanPage />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('ProjectKanbanPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.mocked(clientsApi.list).mockResolvedValue([])
    mockedProjectsApi.list.mockResolvedValue([
      build({ id: 1, name: '案件A', status: 'NOT_STARTED' }),
      build({ id: 2, name: '案件B', status: 'IN_PROGRESS', due_date: '2026-09-10', due_state: 'OVERDUE' }),
    ])
  })

  it('ステータスごとの列にカードを振り分け、納期状態を表示する', async () => {
    renderPage()
    await screen.findByText('案件A')
    const notStarted = screen.getByTestId('kanban-column-NOT_STARTED')
    expect(within(notStarted).getByText('案件A')).toBeInTheDocument()
    const inProgress = screen.getByTestId('kanban-column-IN_PROGRESS')
    expect(within(inProgress).getByText('案件B')).toBeInTheDocument()
    expect(within(inProgress).getByText('超過')).toBeInTheDocument()
    expect(screen.getByTestId('kanban-column-DONE')).toBeInTheDocument()
  })

  it('「ステータス変更」メニューで変更するとAPIが呼ばれ、即時に別の列へ移動する(楽観的更新)', async () => {
    mockedProjectsApi.changeStatus.mockResolvedValue({} as never)
    renderPage()
    await screen.findByText('案件A')
    // 更新後の再取得ではサーバー側の変更後の状態が返る
    mockedProjectsApi.list.mockResolvedValue([
      build({ id: 1, name: '案件A', status: 'DONE' }),
      build({ id: 2, name: '案件B', status: 'IN_PROGRESS', due_date: '2026-09-10', due_state: 'OVERDUE' }),
    ])
    fireEvent.change(screen.getByLabelText('案件Aのステータス変更'), { target: { value: 'DONE' } })
    await waitFor(() => expect(mockedProjectsApi.changeStatus).toHaveBeenCalledWith(1, 'DONE'))
    await waitFor(() => expect(within(screen.getByTestId('kanban-column-DONE')).getByText('案件A')).toBeInTheDocument())
  })

  it('変更に失敗した場合は元の列へ戻し、エラーメッセージを表示する', async () => {
    mockedProjectsApi.changeStatus.mockRejectedValue(new Error('500'))
    renderPage()
    await screen.findByText('案件A')
    fireEvent.change(screen.getByLabelText('案件Aのステータス変更'), { target: { value: 'DONE' } })
    expect(await screen.findByText('ステータスを変更できませんでした')).toBeInTheDocument()
    await waitFor(() =>
      expect(within(screen.getByTestId('kanban-column-NOT_STARTED')).getByText('案件A')).toBeInTheDocument()
    )
  })

  it('現在と同じステータスを選んでもAPIを呼ばない', async () => {
    renderPage()
    await screen.findByText('案件A')
    fireEvent.change(screen.getByLabelText('案件Aのステータス変更'), { target: { value: 'NOT_STARTED' } })
    expect(mockedProjectsApi.changeStatus).not.toHaveBeenCalled()
  })
})
