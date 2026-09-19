import { useEffect, useState } from 'react'
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  Chip,
  Container,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Radio,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material'
import { useNavigate, useParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import AppHeader from '../components/AppHeader'
import { clientsApi } from '../api/clients'
import { extractErrorMessage } from '../api/client'
import { invoicesApi } from '../api/invoices'
import { quotesApi } from '../api/quotes'
import { projectsApi, type ProjectPayload } from '../api/projects'
import {
  PAYMENT_STATUS_LABELS,
  PROJECT_STATUSES,
  PROJECT_STATUS_LABELS,
  QUOTE_STATUS_LABELS,
  type ProjectStatus,
} from '../types'
import { formatCurrency } from '../utils/format'
import { DueStateTag } from '../components/ProjectCommon'
import { PAYMENT_STATUS_COLORS, QUOTE_STATUS_COLORS } from '../theme'

type LinkKind = 'invoice' | 'quote'

interface LinkCandidate {
  id: number
  number: string
  clientName: string
  totalAmount: number
  projectId: number | null
  projectName: string | null
}

const sectionTitleSx = { fontWeight: 600, mb: 1.5, pb: 1, borderBottom: '1px solid #dde1e6' }

export default function ProjectDetailPage() {
  const { id } = useParams()
  const isNew = id === undefined || id === 'new'
  const projectId = isNew ? undefined : Number(id)
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const { data: clients } = useQuery({ queryKey: ['clients'], queryFn: clientsApi.list })
  const { data: project } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId as number),
    enabled: !isNew,
  })

  const [name, setName] = useState('')
  const [clientId, setClientId] = useState<number | null>(null)
  const [status, setStatus] = useState<ProjectStatus>('NOT_STARTED')
  const [dueDate, setDueDate] = useState('')
  const [description, setDescription] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [linkKind, setLinkKind] = useState<LinkKind | null>(null)
  const [selectedCandidateId, setSelectedCandidateId] = useState<number | null>(null)

  useEffect(() => {
    if (project) {
      setName(project.name)
      setClientId(project.client_id)
      setStatus(project.status)
      setDueDate(project.due_date ?? '')
      setDescription(project.description ?? '')
    }
  }, [project])

  const invalidateProjects = () => {
    queryClient.invalidateQueries({ queryKey: ['projects'] })
    queryClient.invalidateQueries({ queryKey: ['project', projectId] })
    queryClient.invalidateQueries({ queryKey: ['invoices'] })
    queryClient.invalidateQueries({ queryKey: ['quotes'] })
  }

  const saveMutation = useMutation({
    mutationFn: (payload: ProjectPayload) =>
      isNew ? projectsApi.create(payload) : projectsApi.update(projectId as number, payload),
    onSuccess: (saved) => {
      setErrorMessage(null)
      invalidateProjects()
      if (isNew) navigate(`/projects/${saved.id}`, { replace: true })
    },
    onError: (error) => setErrorMessage(extractErrorMessage(error)),
  })

  const deleteMutation = useMutation({
    mutationFn: () => projectsApi.remove(projectId as number),
    onSuccess: () => {
      invalidateProjects()
      navigate('/projects', { replace: true })
    },
    onError: (error) => {
      setDeleteDialogOpen(false)
      setErrorMessage(extractErrorMessage(error))
    },
  })

  const linkMutation = useMutation({
    mutationFn: async ({ kind, documentId, target }: { kind: LinkKind; documentId: number; target: number | null }) => {
      if (kind === 'invoice') await invoicesApi.linkProject(documentId, target)
      else await quotesApi.linkProject(documentId, target)
    },
    onSuccess: () => {
      setErrorMessage(null)
      setLinkKind(null)
      setSelectedCandidateId(null)
      invalidateProjects()
    },
    onError: (error) => setErrorMessage(extractErrorMessage(error)),
  })

  const { data: candidates } = useQuery<LinkCandidate[]>({
    queryKey: ['link-candidates', linkKind],
    enabled: linkKind !== null,
    queryFn: async () => {
      if (linkKind === 'invoice') {
        const rows = await invoicesApi.list()
        return rows.map((r) => ({
          id: r.id,
          number: r.invoice_number,
          clientName: r.client_name,
          totalAmount: r.total_amount,
          projectId: r.project_id,
          projectName: r.project_name,
        }))
      }
      const rows = await quotesApi.list()
      return rows.map((r) => ({
        id: r.id,
        number: r.quote_number,
        clientName: r.client_name,
        totalAmount: r.total_amount,
        projectId: r.project_id,
        projectName: r.project_name,
      }))
    },
  })

  const { data: allProjects } = useQuery({ queryKey: ['projects', {}], queryFn: () => projectsApi.list() })

  const handleSave = () => {
    if (name.trim() === '') {
      setErrorMessage('案件名を入力してください')
      return
    }
    saveMutation.mutate({
      name: name.trim(),
      client_id: clientId,
      status,
      due_date: dueDate || null,
      description: description || null,
    })
  }

  const closeLinkDialog = () => {
    setLinkKind(null)
    setSelectedCandidateId(null)
  }

  const selectableCandidates = (candidates ?? []).filter((c) => c.projectId !== projectId)
  const selectedCandidate = selectableCandidates.find((c) => c.id === selectedCandidateId) ?? null
  const projectLabel = (c: LinkCandidate): string => {
    if (c.projectId === null) return '(案件なし)'
    const isDone = allProjects?.find((p) => p.id === c.projectId)?.status === 'DONE'
    return `${c.projectName ?? ''}${isDone ? '(完了)' : ''}`
  }

  const kindLabel = linkKind === 'invoice' ? '請求書' : '見積書'

  return (
    <Box>
      <AppHeader backTo="/projects" backLabel="← 案件一覧へ" />
      <Container maxWidth="lg" sx={{ py: 3 }}>
        <Typography variant="h5" sx={{ mb: 2 }}>
          案件詳細・編集
        </Typography>

        {errorMessage && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {errorMessage}
          </Alert>
        )}

        <Card variant="outlined" sx={{ p: 2.5, mb: 2.5 }}>
          <Typography sx={sectionTitleSx}>案件情報</Typography>
          <Stack spacing={2}>
            <TextField
              label="案件名"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              inputProps={{ maxLength: 100 }}
            />
            <Autocomplete
              options={clients ?? []}
              getOptionLabel={(option) => option.name}
              value={clients?.find((c) => c.id === clientId) ?? null}
              onChange={(_, value) => setClientId(value ? value.id : null)}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              renderInput={(params) => <TextField {...params} label="取引先" />}
            />
            <TextField select label="ステータス" required value={status} onChange={(e) => setStatus(e.target.value as ProjectStatus)}>
              {PROJECT_STATUSES.map((s) => (
                <MenuItem key={s} value={s}>
                  {PROJECT_STATUS_LABELS[s]}
                </MenuItem>
              ))}
            </TextField>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
              <TextField
                label="納期"
                type="date"
                InputLabelProps={{ shrink: true }}
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
              />
              {project && <DueStateTag state={project.due_state} />}
              <Typography color="text.secondary" sx={{ fontSize: 12 }}>
                任意。過去日も入力できます
              </Typography>
            </Box>
            <TextField
              label="概要メモ"
              multiline
              minRows={3}
              placeholder="任意で概要を入力(最大1000文字)"
              inputProps={{ maxLength: 1000 }}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </Stack>
          <Stack direction="row" spacing={1.5} justifyContent="flex-end" sx={{ mt: 2 }}>
            {!isNew && (
              <Button variant="outlined" color="error" onClick={() => setDeleteDialogOpen(true)}>
                削除
              </Button>
            )}
            <Button variant="contained" onClick={handleSave} disabled={saveMutation.isPending}>
              保存
            </Button>
          </Stack>
        </Card>

        {!isNew && project && (
          <>
            <Card variant="outlined" sx={{ p: 2.5, mb: 2.5 }}>
              <Typography sx={sectionTitleSx}>集計サマリー</Typography>
              <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 1.5 }}>
                <SummaryCell label={`見積書(${project.summary.quote_count}件)`} value={formatCurrency(project.summary.quote_total)} />
                <SummaryCell label={`請求書(${project.summary.invoice_count}件)`} value={formatCurrency(project.summary.invoice_total)} />
                <SummaryCell label="入金済み金額" value={formatCurrency(project.summary.paid_total)} color="#15803d" />
                <SummaryCell label="未回収金額" value={formatCurrency(project.summary.unpaid_total)} color="primary.main" />
              </Box>
            </Card>

            <Card variant="outlined" sx={{ p: 2.5, mb: 2.5 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={sectionTitleSx}>
                <span>紐付いた見積書</span>
                <Button size="small" variant="contained" onClick={() => setLinkKind('quote')}>
                  見積書を紐付ける
                </Button>
              </Stack>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>見積書番号</TableCell>
                    <TableCell>発行日</TableCell>
                    <TableCell>有効期限</TableCell>
                    <TableCell align="right">合計金額</TableCell>
                    <TableCell>ステータス</TableCell>
                    <TableCell>操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {project.quotes.map((q) => (
                    <TableRow key={q.id} hover sx={{ cursor: 'pointer' }} onClick={() => navigate(`/quotes/${q.id}`)}>
                      <TableCell>{q.quote_number}</TableCell>
                      <TableCell>{q.issue_date ?? '-'}</TableCell>
                      <TableCell>{q.expiry_date ?? '-'}</TableCell>
                      <TableCell align="right">{formatCurrency(q.total_amount)}</TableCell>
                      <TableCell>
                        <Chip size="small" label={QUOTE_STATUS_LABELS[q.status]} sx={{ backgroundColor: QUOTE_STATUS_COLORS[q.status], color: '#fff' }} />
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => linkMutation.mutate({ kind: 'quote', documentId: q.id, target: null })}
                        >
                          紐付けを解除
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>

            <Card variant="outlined" sx={{ p: 2.5, mb: 2.5 }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center" sx={sectionTitleSx}>
                <span>紐付いた請求書</span>
                <Button size="small" variant="contained" onClick={() => setLinkKind('invoice')}>
                  請求書を紐付ける
                </Button>
              </Stack>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>請求書番号</TableCell>
                    <TableCell>発行日</TableCell>
                    <TableCell>支払期限</TableCell>
                    <TableCell align="right">合計金額</TableCell>
                    <TableCell>入金ステータス</TableCell>
                    <TableCell>操作</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {project.invoices.map((i) => (
                    <TableRow key={i.id} hover sx={{ cursor: 'pointer' }} onClick={() => navigate(`/invoices/${i.id}`)}>
                      <TableCell>{i.invoice_number}</TableCell>
                      <TableCell>{i.issue_date ?? '-'}</TableCell>
                      <TableCell>{i.due_date ?? '-'}</TableCell>
                      <TableCell align="right">{formatCurrency(i.total_amount)}</TableCell>
                      <TableCell>
                        <Chip size="small" label={PAYMENT_STATUS_LABELS[i.payment_status]} sx={{ backgroundColor: PAYMENT_STATUS_COLORS[i.payment_status], color: '#fff' }} />
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => linkMutation.mutate({ kind: 'invoice', documentId: i.id, target: null })}
                        >
                          紐付けを解除
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Card>
          </>
        )}
      </Container>

      <Dialog open={linkKind !== null} onClose={closeLinkDialog} fullWidth maxWidth="md">
        <DialogTitle>{kindLabel}を選択してください</DialogTitle>
        <DialogContent>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: 40 }} />
                <TableCell>{kindLabel}番号</TableCell>
                <TableCell>取引先名</TableCell>
                <TableCell align="right">合計金額</TableCell>
                <TableCell>現在の案件</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {selectableCandidates.map((c) => (
                <TableRow key={c.id} hover sx={{ cursor: 'pointer' }} onClick={() => setSelectedCandidateId(c.id)}>
                  <TableCell>
                    <Radio
                      size="small"
                      checked={selectedCandidateId === c.id}
                      onChange={() => setSelectedCandidateId(c.id)}
                      inputProps={{ 'aria-label': `${c.number}を選択` }}
                    />
                  </TableCell>
                  <TableCell>{c.number}</TableCell>
                  <TableCell>{c.clientName}</TableCell>
                  <TableCell align="right">{formatCurrency(c.totalAmount)}</TableCell>
                  <TableCell sx={{ color: 'text.secondary' }}>{projectLabel(c)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          {selectedCandidate && selectedCandidate.projectId !== null && (
            <Alert severity="warning" sx={{ mt: 2 }}>
              案件「{selectedCandidate.projectName}」から移動します。よろしいですか?
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeLinkDialog}>キャンセル</Button>
          <Button
            variant="contained"
            disabled={!selectedCandidate || linkMutation.isPending}
            onClick={() =>
              selectedCandidate &&
              linkKind &&
              linkMutation.mutate({ kind: linkKind, documentId: selectedCandidate.id, target: projectId as number })
            }
          >
            紐付ける
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle sx={{ fontSize: 16 }}>
          この案件を削除します。紐付いている見積書・請求書・経費は削除されず、「案件なし」に戻ります。
        </DialogTitle>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>キャンセル</Button>
          <Button variant="contained" color="error" onClick={() => deleteMutation.mutate()} disabled={deleteMutation.isPending}>
            削除する
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  )
}

function SummaryCell({ label, value, color }: { label: string; value: string; color?: string }) {
  return (
    <Box sx={{ border: '1px solid #dde1e6', borderRadius: '6px', p: 1.5 }}>
      <Typography sx={{ fontSize: 12, color: 'text.secondary' }}>{label}</Typography>
      <Typography sx={{ fontSize: 18, fontWeight: 700, color }}>{value}</Typography>
    </Box>
  )
}
