import { useState } from 'react'
import { Alert, Box, Button, Card, Container, MenuItem, NativeSelect, TextField, Toolbar, Typography } from '@mui/material'
import { DragDropContext, Draggable, Droppable, type DropResult } from '@hello-pangea/dnd'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import { DueStateTag, ProjectTabs } from '../components/ProjectCommon'
import { clientsApi } from '../api/clients'
import { projectsApi } from '../api/projects'
import { PROJECT_STATUSES, PROJECT_STATUS_LABELS, type ProjectListItem, type ProjectStatus } from '../types'
import { OVERDUE_BACKGROUND, PROJECT_STATUS_COLORS } from '../theme'

const STATUS_CHANGE_ERROR = 'ステータスを変更できませんでした'

export default function ProjectKanbanPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [clientId, setClientId] = useState<number | ''>('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: clientsApi.list })
  const filters = { client_id: clientId === '' ? undefined : clientId }
  const queryKey = ['projects', filters]
  const { data: projects, isError } = useQuery({ queryKey, queryFn: () => projectsApi.list(filters) })

  // 楽観的更新: キャッシュ上のステータスを即時更新し、失敗時は元に戻す(詳細設計書3.14・4.9.3)
  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: ProjectStatus }) => projectsApi.changeStatus(id, status),
    onMutate: async ({ id, status }) => {
      setErrorMessage(null)
      await queryClient.cancelQueries({ queryKey })
      const previous = queryClient.getQueryData<ProjectListItem[]>(queryKey)
      queryClient.setQueryData<ProjectListItem[]>(queryKey, (old) =>
        old?.map((p) => (p.id === id ? { ...p, status } : p))
      )
      return { previous }
    },
    onError: (_error, _variables, context) => {
      queryClient.setQueryData(queryKey, context?.previous)
      setErrorMessage(STATUS_CHANGE_ERROR)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] })
    },
  })

  const changeStatus = (project: ProjectListItem, status: ProjectStatus) => {
    if (project.status === status) return
    statusMutation.mutate({ id: project.id, status })
  }

  const handleDragEnd = (result: DropResult) => {
    const { source, destination, draggableId } = result
    if (!destination || destination.droppableId === source.droppableId) return
    const project = projects?.find((p) => String(p.id) === draggableId)
    if (project) changeStatus(project, destination.droppableId as ProjectStatus)
  }

  return (
    <Box>
      <AppHeader backTo="/" backLabel="← ホームへ" />
      <Container maxWidth="xl" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          案件
        </Typography>
        <ProjectTabs active="kanban" />
        <Toolbar disableGutters sx={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 1.5, mb: 1 }}>
          <TextField
            select
            size="small"
            label="取引先"
            sx={{ minWidth: 180 }}
            value={clientId}
            onChange={(e) => setClientId(e.target.value === '' ? '' : Number(e.target.value))}
          >
            <MenuItem value="">すべて</MenuItem>
            {clients?.map((c) => (
              <MenuItem key={c.id} value={c.id}>
                {c.name}
              </MenuItem>
            ))}
          </TextField>
          <Button variant="contained" onClick={() => navigate('/projects/new')}>
            新規案件
          </Button>
        </Toolbar>
        <Typography variant="body2" color="text.secondary" sx={{ fontSize: 12, mb: 1.5 }}>
          カードをつかんで別の列へドラッグすると、ステータスが変わります(カード内の「ステータス変更」メニューでも変更できます)。
        </Typography>
        {errorMessage && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errorMessage}
          </Alert>
        )}
        {isError && (
          <Alert severity="error" sx={{ mb: 2 }}>
            案件を取得できませんでした。
          </Alert>
        )}

        <DragDropContext onDragEnd={handleDragEnd}>
          <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 1.5 }}>
            {PROJECT_STATUSES.map((status) => {
              const columnProjects = (projects ?? []).filter((p) => p.status === status)
              return (
                <Droppable droppableId={status} key={status}>
                  {(provided, snapshot) => (
                    <Box
                      ref={provided.innerRef}
                      {...provided.droppableProps}
                      data-testid={`kanban-column-${status}`}
                      sx={{
                        backgroundColor: snapshot.isDraggingOver ? '#e1eef5' : '#e9edf1',
                        outline: snapshot.isDraggingOver ? '2px dashed #2c5f7c' : 'none',
                        outlineOffset: '-2px',
                        borderRadius: '6px',
                        p: 1.25,
                        minHeight: 320,
                      }}
                    >
                      <Box
                        sx={{
                          color: '#fff',
                          fontWeight: 700,
                          fontSize: 14,
                          px: 1.5,
                          py: 0.75,
                          borderRadius: '4px',
                          mb: 1.25,
                          display: 'flex',
                          justifyContent: 'space-between',
                          backgroundColor: PROJECT_STATUS_COLORS[status],
                        }}
                      >
                        {PROJECT_STATUS_LABELS[status]}
                        <span>{columnProjects.length}</span>
                      </Box>
                      {columnProjects.map((project, index) => (
                        <Draggable draggableId={String(project.id)} index={index} key={project.id}>
                          {(dragProvided, dragSnapshot) => (
                            <Card
                              ref={dragProvided.innerRef}
                              {...dragProvided.draggableProps}
                              {...dragProvided.dragHandleProps}
                              variant="outlined"
                              onClick={() => navigate(`/projects/${project.id}`)}
                              sx={{
                                p: 1.25,
                                mb: 1.25,
                                borderLeft: '4px solid',
                                borderLeftColor: project.due_state === 'OVERDUE' ? 'error.main' : '#dde1e6',
                                backgroundColor: project.due_state === 'OVERDUE' ? OVERDUE_BACKGROUND : '#fff',
                                boxShadow: dragSnapshot.isDragging ? 6 : undefined,
                                cursor: 'grab',
                              }}
                            >
                              <Typography sx={{ fontWeight: 600, fontSize: 14 }}>{project.name}</Typography>
                              <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>
                                {project.client_name ?? '(取引先なし)'}
                              </Typography>
                              <Typography sx={{ fontSize: 12, mb: 0.75 }}>
                                {project.due_date ? (
                                  <>
                                    納期: {project.due_date}
                                    <DueStateTag state={project.due_state} />
                                  </>
                                ) : (
                                  <Typography component="span" color="text.secondary" sx={{ fontSize: 12 }}>
                                    納期: 未設定
                                  </Typography>
                                )}
                              </Typography>
                              <NativeSelect
                                value=""
                                inputProps={{ 'aria-label': `${project.name}のステータス変更` }}
                                onClick={(e) => e.stopPropagation()}
                                onChange={(e) => changeStatus(project, e.target.value as ProjectStatus)}
                                sx={{ fontSize: 12 }}
                              >
                                <option value="">ステータス変更</option>
                                {PROJECT_STATUSES.map((s) => (
                                  <option key={s} value={s}>
                                    {PROJECT_STATUS_LABELS[s]}
                                  </option>
                                ))}
                              </NativeSelect>
                            </Card>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </Box>
                  )}
                </Droppable>
              )
            })}
          </Box>
        </DragDropContext>
      </Container>
    </Box>
  )
}
