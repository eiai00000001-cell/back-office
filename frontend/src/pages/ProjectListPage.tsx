import { useMemo, useState } from 'react'
import { Box, Button, Card, Container, MenuItem, Table, TableBody, TableCell, TableHead, TableRow, TextField, Toolbar, Typography } from '@mui/material'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import { DueStateTag, ProjectStatusChip, ProjectTabs } from '../components/ProjectCommon'
import { clientsApi } from '../api/clients'
import { projectsApi } from '../api/projects'
import { PROJECT_STATUS_LABELS, type ProjectStatus } from '../types'
import { OVERDUE_BACKGROUND } from '../theme'

export default function ProjectListPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<ProjectStatus | ''>('')
  const [clientId, setClientId] = useState<number | ''>('')

  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: clientsApi.list })
  const filters = useMemo(
    () => ({
      status: status === '' ? undefined : status,
      client_id: clientId === '' ? undefined : clientId,
    }),
    [status, clientId]
  )
  const { data: projects, isError } = useQuery({
    queryKey: ['projects', filters],
    queryFn: () => projectsApi.list(filters),
  })

  return (
    <Box>
      <AppHeader backTo="/" backLabel="← ホームへ" />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          案件
        </Typography>
        <ProjectTabs active="list" />
        <Card variant="outlined" sx={{ p: 2.5 }}>
          <Toolbar disableGutters sx={{ justifyContent: 'space-between', flexWrap: 'wrap', gap: 1.5, mb: 1 }}>
            <Box sx={{ display: 'flex', gap: 1.5, flexWrap: 'wrap' }}>
              <TextField
                select
                size="small"
                label="ステータス"
                sx={{ minWidth: 180 }}
                value={status}
                onChange={(e) => setStatus(e.target.value as ProjectStatus | '')}
              >
                <MenuItem value="">すべて</MenuItem>
                {Object.entries(PROJECT_STATUS_LABELS).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    {label}
                  </MenuItem>
                ))}
              </TextField>
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
            </Box>
            <Button variant="contained" onClick={() => navigate('/projects/new')}>
              新規案件
            </Button>
          </Toolbar>
          <Typography variant="body2" color="text.secondary" sx={{ fontSize: 12, mb: 1.25 }}>
            納期の近い順(納期未設定は末尾)で表示しています。
          </Typography>
          {isError && (
            <Typography color="error" sx={{ fontSize: 13, mb: 1 }}>
              案件を取得できませんでした。
            </Typography>
          )}
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>案件名</TableCell>
                <TableCell>取引先名</TableCell>
                <TableCell>ステータス</TableCell>
                <TableCell>納期</TableCell>
                <TableCell>紐付け件数(見積 / 請求)</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {projects?.map((project) => (
                <TableRow
                  key={project.id}
                  hover
                  onClick={() => navigate(`/projects/${project.id}`)}
                  sx={{ cursor: 'pointer', backgroundColor: project.due_state === 'OVERDUE' ? OVERDUE_BACKGROUND : undefined }}
                >
                  <TableCell>{project.name}</TableCell>
                  <TableCell>{project.client_name ?? <Typography component="span" color="text.secondary" sx={{ fontSize: 13 }}>(取引先なし)</Typography>}</TableCell>
                  <TableCell>
                    <ProjectStatusChip status={project.status} />
                  </TableCell>
                  <TableCell>
                    {project.due_date ?? <Typography component="span" color="text.secondary" sx={{ fontSize: 13 }}>未設定</Typography>}
                    <DueStateTag state={project.due_state} />
                  </TableCell>
                  <TableCell>
                    見積{project.quote_count}件 / 請求{project.invoice_count}件
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </Container>
    </Box>
  )
}
